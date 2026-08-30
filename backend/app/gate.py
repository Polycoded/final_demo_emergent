"""Trainable 12 -> 24 -> 4 gate, isolated from detector training."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .schemas import FrameFeatures, GateResult

EXPERTS = ("crowd_geometry", "temporal_volatility", "motion_change", "recovery_value")


def vector(f: FrameFeatures) -> np.ndarray:
    return np.array(
        [
            f.person_count / 40,
            f.occupancy_ratio,
            f.confidence_mean,
            f.confidence_variance,
            f.count_delta,
            f.motion_energy,
            f.blur,
            f.blockiness,
            min(f.frame_age_ms / 2000, 1),
            min(f.queue_depth / 10, 1),
            f.accelerator_utilization or 0,
            f.expert_load,
        ]
    )


@dataclass
class LearnedGate:
    w1: np.ndarray
    b1: np.ndarray
    w2: np.ndarray
    b2: np.ndarray
    checkpoint_id: str = "untrained"

    @classmethod
    def fallback(cls):
        rng = np.random.default_rng(20260825)
        return cls(
            rng.normal(0, 0.08, (12, 24)), np.zeros(24), rng.normal(0, 0.08, (24, 4)), np.zeros(4)
        )

    @classmethod
    def load(cls, path: Path) -> "LearnedGate":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            *(np.asarray(payload[key], dtype=np.float64) for key in ("w1", "b1", "w2", "b2")),
            checkpoint_id=payload.get("checkpoint_id", path.stem),
        )

    def predict(self, features: FrameFeatures) -> GateResult:
        hidden = np.maximum(0, vector(features) @ self.w1 + self.b1)
        logits = hidden @ self.w2 + self.b2
        scores = 1 / (1 + np.exp(-logits))
        mapping = dict(zip(EXPERTS, map(float, scores), strict=True))
        selected = sorted(mapping, key=mapping.get, reverse=True)[:2]
        return GateResult(
            scores=mapping,
            selected=selected,
            utility=min(
                1.0,
                0.6 * sum(mapping[k] for k in selected)
                + 0.25 * (1 - features.confidence_mean)
                + 0.15 * features.motion_energy,
            ),
        )

    def save(self, path: Path, checkpoint_id: str = "event-time-gate") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "checkpoint_id": checkpoint_id,
                    **{key: getattr(self, key).tolist() for key in ("w1", "b1", "w2", "b2")},
                }
            ),
            encoding="utf-8",
        )

    def train(self, inputs: np.ndarray, targets: np.ndarray, epochs: int, rate: float) -> None:
        for _ in range(epochs):
            hidden_raw = inputs @ self.w1 + self.b1
            hidden = np.maximum(0, hidden_raw)
            logits = hidden @ self.w2 + self.b2
            probabilities = 1 / (1 + np.exp(-logits))
            error = (probabilities - targets) / len(inputs)
            grad_w2 = hidden.T @ error
            grad_b2 = error.sum(axis=0)
            hidden_error = (error @ self.w2.T) * (hidden_raw > 0)
            self.w2 -= rate * grad_w2
            self.b2 -= rate * grad_b2
            self.w1 -= rate * (inputs.T @ hidden_error)
            self.b1 -= rate * hidden_error.sum(axis=0)
