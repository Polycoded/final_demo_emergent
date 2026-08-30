"""Offline teacher pass: label every feed in every synchronized window."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2

from .detectors import DetectorPair
from .vision import OpenCvFeatureExtractor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=Path, default=Path("assets/scenarios"))
    parser.add_argument("--light-model", type=Path, default=Path("models/yolox_nano.onnx"))
    parser.add_argument("--deep-model", type=Path, default=Path("models/yolox_tiny.onnx"))
    parser.add_argument("--output", type=Path, default=Path("data/labelled-workload.jsonl"))
    parser.add_argument("--windows", type=int, default=30)
    args = parser.parse_args()
    paths = {
        "A": args.scenarios / "feed-a-clear.avi",
        "B": args.scenarios / "feed-b-degraded.avi",
        "C": args.scenarios / "feed-c-temporal.avi",
    }
    captures = {key: cv2.VideoCapture(str(path)) for key, path in paths.items()}
    extractors = {key: OpenCvFeatureExtractor(key) for key in paths}
    detectors = DetectorPair(str(args.deep_model), str(args.light_model))
    start, rows = datetime.now(UTC), []
    for window in range(args.windows):
        for feed_id, capture in captures.items():
            ok, frame = capture.read()
            if not ok:
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Could not read {paths[feed_id]}")
            light, deep = detectors.light.detect(frame), detectors.deep.detect(frame)
            features = extractors[feed_id].analyze(frame)
            features.captured_at = start + timedelta(seconds=window)
            features.person_count, features.confidence_mean = light.count, light.confidence_mean
            disagreement = detectors.disagreement(light, deep)
            targets = SageTargets.from_features(features, disagreement)
            rows.append(
                {
                    "window": str(window),
                    "teacher_disagreement": disagreement,
                    "light_inference_ms": light.inference_ms,
                    "deep_inference_ms": deep.inference_ms,
                    "expert_targets": targets,
                    "feature": features.model_dump(mode="json"),
                }
            )
    for capture in captures.values():
        capture.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    print(f"Labelled {len(rows)} feed-windows with provider {detectors.deep.provider}")


class SageTargets:
    @staticmethod
    def from_features(features, disagreement: float) -> dict[str, float]:
        return {
            "crowd_geometry": min(1, 0.2 + features.occupancy_ratio) * disagreement,
            "temporal_volatility": min(1, 0.2 + features.count_delta + features.confidence_variance)
            * disagreement,
            "motion_change": min(1, 0.2 + features.motion_energy) * disagreement,
            "recovery_value": min(
                1, 0.2 + features.blur + features.blockiness + (1 - features.confidence_mean)
            )
            * disagreement,
        }


if __name__ == "__main__":
    main()
