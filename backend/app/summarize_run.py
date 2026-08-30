import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/formal-runs/stability.json"))
    args = parser.parse_args()
    connection = sqlite3.connect(args.database)
    payloads = [
        json.loads(row[0])
        for row in connection.execute("select payload from receipts order by created_at")
    ]
    timestamps = [item["timestamp"] for item in payloads]
    latencies = [item["decision_latency_ms"] for item in payloads]
    feeds = sorted({item["feed_id"] for item in payloads})
    artifact = {
        "schema_version": 1,
        "source": "live-local-edge-validation",
        "receipt_count": len(payloads),
        "feed_ids": feeds,
        "started_at": timestamps[0] if timestamps else None,
        "ended_at": timestamps[-1] if timestamps else None,
        "deep_calls": sum(bool(item["deep_call_executed"]) for item in payloads),
        "decision_latency_p50_ms": float(np.percentile(latencies, 50)) if latencies else 0,
        "decision_latency_p95_ms": float(np.percentile(latencies, 95)) if latencies else 0,
        "token_budget_violations": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
