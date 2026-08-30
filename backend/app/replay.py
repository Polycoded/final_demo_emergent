"""CLI entry point for a signed-off JSONL workload replay."""

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .benchmark import run_equal_budget_replay
from .gate import LearnedGate
from .schemas import FrameFeatures


def main() -> None:
    parser = argparse.ArgumentParser(description="CAHMA equal-budget policy replay")
    parser.add_argument(
        "workload", type=Path, help="JSONL records with feature and teacher_disagreement fields"
    )
    parser.add_argument("--budget", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("benchmark-result.json"))
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args()
    windows: defaultdict[str, list[FrameFeatures]] = defaultdict(list)
    labels: dict[tuple[str, str], float] = {}
    for line in args.workload.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        feature = FrameFeatures.model_validate(record["feature"])
        window = record.get("window", feature.captured_at.isoformat())
        windows[window].append(feature)
        labels[(feature.feed_id, feature.captured_at.isoformat())] = float(
            record.get("teacher_disagreement", 0.0)
        )
    result = [
        item.__dict__
        for item in run_equal_budget_replay(
            list(windows.values()),
            labels,
            args.budget,
            LearnedGate.load(args.checkpoint) if args.checkpoint else None,
        )
    ]
    artifact = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "workload_sha256": hashlib.sha256(args.workload.read_bytes()).hexdigest(),
        "window_count": len(windows),
        "budget_per_window": args.budget,
        "results": result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
