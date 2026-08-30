"""Edge-local, privacy-preserving frame feature extraction.

The default HOG detector is a baseline adapter. Deployments should replace it
with a validated local detector through the same `analyze` contract.
"""

from collections import deque
from datetime import UTC, datetime

import cv2
import numpy as np

from .schemas import FrameFeatures


class OpenCvFeatureExtractor:
    def __init__(self, feed_id: str):
        self.feed_id = feed_id
        self.previous_gray: np.ndarray | None = None
        self.counts: deque[int] = deque(maxlen=8)
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    @staticmethod
    def _quality(gray: np.ndarray) -> tuple[float, float]:
        laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blur = max(0.0, min(1.0, 1.0 - laplacian_variance / 350.0))
        resized = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        restored = cv2.resize(
            resized, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST
        )
        blockiness = max(
            0.0, min(1.0, float(np.mean(np.abs(gray.astype(np.float32) - restored))) / 48.0)
        )
        return blur, blockiness

    def analyze(self, frame: np.ndarray, queue_depth: int = 0) -> FrameFeatures:
        captured_at = datetime.now(UTC)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if frame.shape[0] < 128 or frame.shape[1] < 64:
            boxes, weights = (), ()
        else:
            boxes, weights = self.hog.detectMultiScale(
                frame, winStride=(8, 8), padding=(8, 8), scale=1.05
            )
        count = len(boxes)
        confidence = float(np.mean(weights)) if len(weights) else 0.0
        confidence = max(0.0, min(1.0, confidence))
        motion = 0.0
        if self.previous_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self.previous_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            motion = max(
                0.0, min(1.0, float(np.mean(cv2.magnitude(flow[..., 0], flow[..., 1])) / 6.0))
            )
        self.previous_gray = gray
        prior = self.counts[-1] if self.counts else count
        self.counts.append(count)
        blur, blockiness = self._quality(gray)
        height, width = gray.shape
        area = sum(w * h for (_, _, w, h) in boxes)
        return FrameFeatures(
            feed_id=self.feed_id,
            captured_at=captured_at,
            person_count=count,
            confidence_mean=confidence,
            confidence_variance=max(0.0, min(1.0, float(np.var(weights)))) if len(weights) else 0.0,
            occupancy_ratio=max(0.0, min(1.0, area / (width * height))),
            count_delta=min(1.0, abs(count - prior) / 10),
            motion_energy=motion,
            blur=blur,
            blockiness=blockiness,
            frame_age_ms=0,
            queue_depth=queue_depth,
            accelerator_utilization=None,
            expert_load=0,
        )
