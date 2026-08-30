"""Frozen scalar Router-v2 runtime with a strict, hash-verified feature contract."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .schemas import FrameFeatures, GateResult

FEATURE_NAMES = (
    "person_count",
    "occupancy_ratio",
    "confidence_mean",
    "confidence_variance",
    "count_delta",
    "motion_energy",
    "blur",
    "blockiness",
    "frame_age_ms",
    "queue_depth",
    "accelerator_utilization",
    "expert_load",
)


class Regressor(Protocol):
    def predict(self, values: list[list[float]]): ...


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def transform(features: FrameFeatures) -> list[float]:
    """Apply the frozen Review-1 transform in its exact documented order."""
    raw = [getattr(features, name) for name in FEATURE_NAMES]
    if any(value is None for value in raw):
        raise ValueError("Scalar router requires all 12 features")
    if any(not math.isfinite(float(value)) for value in raw):
        raise ValueError("Scalar router features must be finite")
    return [
        _clip(max(0.0, float(features.person_count)) / 40.0),
        _clip(features.occupancy_ratio),
        _clip(features.confidence_mean),
        _clip(features.confidence_variance),
        _clip(abs(float(features.count_delta)) / 40.0),
        _clip(features.motion_energy),
        _clip(features.blur),
        _clip(features.blockiness),
        _clip(float(features.frame_age_ms) / 2000.0),
        _clip(float(features.queue_depth) / 10.0),
        _clip(float(features.accelerator_utilization)),
        _clip(features.expert_load),
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class ScalarUtilityGate:
    model: Regressor
    checkpoint_id: str
    checkpoint_sha256: str

    @classmethod
    def load(cls, path: Path, expected_sha256: str) -> ScalarUtilityGate:
        actual = sha256(path)
        if actual.lower() != expected_sha256.lower():
            raise ValueError(
                f"Scalar router hash mismatch: expected {expected_sha256}, got {actual}"
            )
        import joblib

        return cls(joblib.load(path), path.stem, actual)

    def predict(self, features: FrameFeatures) -> GateResult:
        utility = float(self.model.predict([transform(features)])[0])
        if not math.isfinite(utility):
            raise ValueError("Scalar router produced a non-finite utility")
        return GateResult(
            scores={"predicted_proxy_utility": utility},
            selected=["tiny_over_nano"],
            utility=utility,
        )
