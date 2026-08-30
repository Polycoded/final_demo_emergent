from dataclasses import dataclass
from itertools import pairwise
from time import perf_counter

import cv2
import numpy as np
import onnxruntime as ort


@dataclass
class DetectionResult:
    count: int
    confidence_mean: float
    inference_ms: float
    boxes_xyxy: tuple[tuple[float, float, float, float], ...] = ()
    confidence_variance: float = 0.0


def occupancy_union(
    boxes: tuple[tuple[float, float, float, float], ...], width: int, height: int
) -> float:
    """Return clamped union area of original-pixel boxes divided by frame area."""
    if width <= 0 or height <= 0 or not boxes:
        return 0.0
    valid = []
    for x1, y1, x2, y2 in boxes:
        left, right = sorted((max(0.0, min(width, x1)), max(0.0, min(width, x2))))
        top, bottom = sorted((max(0.0, min(height, y1)), max(0.0, min(height, y2))))
        if right > left and bottom > top:
            valid.append((left, top, right, bottom))
    x_edges = sorted({edge for box in valid for edge in (box[0], box[2])})
    area = 0.0
    for left, right in pairwise(x_edges):
        intervals = sorted(
            (top, bottom)
            for x1, top, x2, bottom in valid
            if x1 < right and x2 > left
        )
        covered = 0.0
        if intervals:
            start, end = intervals[0]
            for next_start, next_end in intervals[1:]:
                if next_start > end:
                    covered += end - start
                    start, end = next_start, next_end
                else:
                    end = max(end, next_end)
            covered += end - start
        area += (right - left) * covered
    return max(0.0, min(1.0, area / (width * height)))


class HogPersonDetector:
    def __init__(self, scale: float):
        self.scale = scale
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame: np.ndarray) -> DetectionResult:
        started = perf_counter()
        resized = cv2.resize(frame, (0, 0), fx=self.scale, fy=self.scale)
        if resized.shape[0] < 128 or resized.shape[1] < 64:
            return DetectionResult(0, 0, (perf_counter() - started) * 1000)
        boxes, weights = self.hog.detectMultiScale(
            resized, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        confidence = float(np.mean(weights)) if len(weights) else 0.0
        original_boxes = tuple(
            (x / self.scale, y / self.scale, (x + w) / self.scale, (y + h) / self.scale)
            for x, y, w, h in boxes
        )
        clipped_weights = np.clip(np.asarray(weights, dtype=np.float64), 0.0, 1.0)
        return DetectionResult(
            len(boxes),
            max(0.0, min(1.0, confidence)),
            (perf_counter() - started) * 1000,
            original_boxes,
            float(np.var(clipped_weights)) if len(clipped_weights) else 0.0,
        )


class DetectorPair:
    def __init__(self, deep_model: str | None = None, light_model: str | None = None):
        self.light = YoloXOnnxDetector(light_model) if light_model else HogPersonDetector(0.5)
        self.deep = YoloXOnnxDetector(deep_model) if deep_model else HogPersonDetector(1.0)

    @staticmethod
    def disagreement(light: DetectionResult, deep: DetectionResult) -> float:
        count_gap = abs(light.count - deep.count) / max(1, deep.count, light.count)
        return min(1.0, 0.7 * count_gap + 0.3 * abs(light.confidence_mean - deep.confidence_mean))


class YoloXOnnxDetector:
    def __init__(self, model_path: str, score_threshold: float = 0.25):
        available = ort.get_available_providers()
        providers = [
            name
            for name in ("DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider")
            if name in available
        ]
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        input_shape = self.session.get_inputs()[0].shape
        if not isinstance(input_shape[-1], int) or input_shape[-1] != input_shape[-2]:
            raise ValueError("YOLOX ONNX input must have a fixed square resolution")
        self.input_size = input_shape[-1]
        self.score_threshold = score_threshold
        self.provider = self.session.get_providers()[0]
        grids = []
        strides = []
        for stride in (8, 16, 32):
            level = self.input_size // stride
            grid_y, grid_x = np.meshgrid(np.arange(level), np.arange(level), indexing="ij")
            grids.append(np.stack((grid_x, grid_y), axis=-1).reshape(-1, 2))
            strides.append(np.full((level * level, 1), stride))
        self.grid = np.concatenate(grids)
        self.strides = np.concatenate(strides)

    def detect(self, frame: np.ndarray) -> DetectionResult:
        started = perf_counter()
        height, width = frame.shape[:2]
        ratio = min(self.input_size / height, self.input_size / width)
        resized = cv2.resize(frame, (int(width * ratio), int(height * ratio)))
        padded = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)
        padded[: resized.shape[0], : resized.shape[1]] = resized
        tensor = padded.transpose(2, 0, 1)[None].astype(np.float32)
        prediction = self.session.run(None, {self.input_name: tensor})[0][0]
        if len(prediction) != len(self.grid):
            raise ValueError(
                f"YOLOX grid mismatch: {len(prediction)} predictions for {len(self.grid)} cells"
            )
        decoded = prediction[:, :4].copy()
        decoded[:, :2] = (decoded[:, :2] + self.grid) * self.strides
        decoded[:, 2:4] = np.exp(np.clip(decoded[:, 2:4], -20, 20)) * self.strides
        person_scores = prediction[:, 4] * prediction[:, 5]
        keep = person_scores >= self.score_threshold
        candidates = decoded[keep]
        scores = person_scores[keep]
        boxes = []
        for center_x, center_y, box_width, box_height in candidates:
            boxes.append(
                [
                    float(center_x - box_width / 2),
                    float(center_y - box_height / 2),
                    float(box_width),
                    float(box_height),
                ]
            )
        indices = (
            cv2.dnn.NMSBoxes(boxes, scores.tolist(), self.score_threshold, 0.45) if boxes else []
        )
        selected_indices = np.asarray(indices).reshape(-1) if len(indices) else np.asarray([], int)
        selected_scores = scores[selected_indices] if len(selected_indices) else np.asarray([])
        original_boxes = []
        for index in selected_indices:
            x, y, box_width, box_height = boxes[int(index)]
            original = (
                max(0.0, min(float(width), x / ratio)),
                max(0.0, min(float(height), y / ratio)),
                max(0.0, min(float(width), (x + box_width) / ratio)),
                max(0.0, min(float(height), (y + box_height) / ratio)),
            )
            if original[2] > original[0] and original[3] > original[1]:
                original_boxes.append(original)
        confidence = float(selected_scores.mean()) if len(selected_scores) else 0.0
        return DetectionResult(
            len(original_boxes),
            confidence,
            (perf_counter() - started) * 1000,
            tuple(original_boxes),
            float(selected_scores.var()) if len(selected_scores) else 0.0,
        )
