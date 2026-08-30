import argparse
import json
from pathlib import Path

import numpy as np

from .gate import EXPERTS, LearnedGate, vector
from .schemas import FrameFeatures


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the tiny 12-24-4 SAGE gate")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("checkpoints/sage-gate.json"))
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--rate", type=float, default=0.04)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines()]
    if not records:
        raise SystemExit("Training dataset is empty")
    inputs = np.stack([vector(FrameFeatures.model_validate(item["feature"])) for item in records])
    targets = np.asarray(
        [[float(item["expert_targets"].get(name, 0)) for name in EXPERTS] for item in records]
    )
    if np.any(targets.sum(axis=1) == 0):
        raise SystemExit("Every sample requires at least one positive expert target")
    targets = np.clip(targets, 0, 1)
    gate = LearnedGate.fallback()
    gate.train(inputs, targets, args.epochs, args.rate)
    gate.save(args.output, checkpoint_id=f"event-time-{len(records)}-samples")
    print(f"Saved {args.output} from {len(records)} samples")


if __name__ == "__main__":
    main()
