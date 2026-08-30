from __future__ import annotations

from datetime import UTC, datetime

import cv2
import numpy as np

from .v2_schemas import ObserverSignals, TaskId


class CheapObserverV2:
    """Task-independent, CPU-oriented observer with per-camera temporal history."""

    def __init__(self, camera_id: str, task_id: TaskId) -> None:
        self.camera_id = camera_id
        self.task_id = task_id
        self.previous_gray: np.ndarray | None = None
        self.last_deep_at: datetime | None = None
        self.previous_count: int | None = None
        self.previous_confidence: float | None = None

    def record_production_result(
        self, count: int | None, confidence: float | None, at: datetime | None = None
    ) -> None:
        self.previous_count = count
        self.previous_confidence = confidence
        self.last_deep_at = at or datetime.now(UTC)

    def analyze(
        self,
        frame: np.ndarray,
        queue_depth: int = 0,
        gpu_utilization: float = 0,
        captured_at: datetime | None = None,
    ) -> ObserverSignals:
        captured = captured_at or datetime.now(UTC)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
        if self.previous_gray is None:
            difference = 0.0
        else:
            difference = float(np.mean(cv2.absdiff(small, self.previous_gray)) / 255.0)
        self.previous_gray = small
        laplacian_variance = float(cv2.Laplacian(small, cv2.CV_64F).var())
        blur = 1.0 / (1.0 + laplacian_variance / 120.0)
        brightness = float(np.mean(small) / 255.0)
        contrast = float(min(1.0, np.std(small) / 64.0))
        histogram = cv2.calcHist([small], [0], None, [64], [0, 256]).ravel()
        probabilities = histogram / max(1.0, histogram.sum())
        probabilities = probabilities[probabilities > 0]
        entropy = float(min(1.0, -np.sum(probabilities * np.log2(probabilities)) / 6.0))
        motion = float(min(1.0, difference * 4.0))
        scene_change = float(min(1.0, difference * 2.0))
        since_deep = (
            max(0.0, (captured - self.last_deep_at).total_seconds() * 1000)
            if self.last_deep_at
            else 60_000.0
        )
        return ObserverSignals(
            camera_id=self.camera_id,
            task_id=self.task_id,
            captured_at=captured,
            motion=motion,
            frame_difference=difference,
            blur=blur,
            brightness=brightness,
            contrast=contrast,
            entropy=entropy,
            scene_change=scene_change,
            time_since_deep_ms=since_deep,
            previous_count=self.previous_count,
            previous_confidence=self.previous_confidence,
            queue_depth=queue_depth,
            gpu_utilization=gpu_utilization,
        )
