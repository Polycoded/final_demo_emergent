"""Generate a deterministic, clearly-labelled local demo workload. Not benchmark evidence."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("demo-workload.jsonl"))
    parser.add_argument("--windows", type=int, default=30)
    args = parser.parse_args()
    start = datetime.now(UTC)
    rows = []
    for index in range(args.windows):
        for feed_id, confidence, motion, blur, disagreement in (
            ("A", 0.91, 0.22, 0.08, 0.12),
            (
                "B",
                0.58 if 8 <= index < 18 else 0.81,
                0.16,
                0.65 if 8 <= index < 18 else 0.12,
                0.66 if 8 <= index < 18 else 0.10,
            ),
            ("C", 0.86, 0.86 if index < 8 else 0.34, 0.10, 0.81 if index < 8 else 0.20),
        ):
            captured = start + timedelta(seconds=index)
            rows.append(
                {
                    "window": str(index),
                    "teacher_disagreement": disagreement,
                    "expert_targets": {
                        "crowd_geometry": 0.2,
                        "temporal_volatility": 0.7 if motion > 0.6 else 0.2,
                        "motion_change": 0.9 if motion > 0.6 else 0.15,
                        "recovery_value": 0.9 if blur > 0.5 else 0.15,
                    },
                    "feature": {
                        "feed_id": feed_id,
                        "captured_at": captured.isoformat(),
                        "person_count": 12,
                        "confidence_mean": confidence,
                        "confidence_variance": 0.18,
                        "occupancy_ratio": 0.42,
                        "count_delta": 0.35,
                        "motion_energy": motion,
                        "blur": blur,
                        "blockiness": blur / 2,
                        "frame_age_ms": 80,
                        "queue_depth": 1,
                        "accelerator_utilization": None,
                        "expert_load": 0.1,
                    },
                }
            )
    args.output.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
