"""Three-camera v2 demo driver using cheap observers and one resident model service."""

from __future__ import annotations

import argparse
import base64
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import cv2

from .observer_v2 import CheapObserverV2
from .v2_schemas import TaskId


def post(endpoint: str, api_key: str, payload: object, timeout: float = 15) -> dict:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-CAHMA-Key": api_key},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="CAHMA v2 multi-camera demo orchestrator")
    parser.add_argument("--source-a", required=True)
    parser.add_argument("--source-b", required=True)
    parser.add_argument("--source-c", required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8080")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--sample-fps", type=float, default=1)
    parser.add_argument("--evidence", type=Path, default=Path("data/v2-demo.jsonl"))
    args = parser.parse_args()
    sources = {"A": args.source_a, "B": args.source_b, "C": args.source_c}
    captures = {camera: cv2.VideoCapture(path) for camera, path in sources.items()}
    observers = {camera: CheapObserverV2(camera, TaskId.PERSON) for camera in sources}
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    interval = 1 / max(0.1, args.sample_fps)
    try:
        while True:
            started = time.monotonic()
            frames = {}
            observations = []
            for camera_id, capture in captures.items():
                ok, frame = capture.read()
                if not ok:
                    capture.release()
                    capture = cv2.VideoCapture(sources[camera_id])
                    captures[camera_id] = capture
                    ok, frame = capture.read()
                if not ok:
                    continue
                frames[camera_id] = frame
                observations.append(
                    observers[camera_id].analyze(frame).model_dump(mode="json")
                )
                source_fps = capture.get(cv2.CAP_PROP_FPS) or args.sample_fps
                for _ in range(max(0, round(source_fps / args.sample_fps) - 1)):
                    capture.grab()
            if len(observations) != len(sources):
                time.sleep(1)
                continue
            try:
                decision = post(
                    f"{args.api}/v2/schedule", args.api_key, observations
                )
                selected = decision["selected_camera_id"]
                ok, encoded = cv2.imencode(".jpg", frames[selected], [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ok:
                    raise RuntimeError("Could not encode selected frame")
                inference = post(
                    f"{args.api}/v2/models/{decision['selected_model_id']}/infer",
                    args.api_key,
                    {
                        "camera_id": selected,
                        "decision_id": decision["decision_id"],
                        "frame_base64": base64.b64encode(encoded).decode(),
                    },
                    timeout=20,
                )
                observers[selected].record_production_result(
                    inference.get("person_count"), inference.get("confidence_mean")
                )
                record = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "decision": decision,
                    "inference": inference,
                }
                with args.evidence.open("a", encoding="utf-8") as output:
                    output.write(json.dumps(record) + "\n")
                print(
                    f"{decision['decision_id']} {selected} "
                    f"{decision['reason_code']} {inference['inference_ms']:.1f} ms",
                    flush=True,
                )
            except Exception as error:  # noqa: BLE001 - demo must recover from runtime restart
                print(f"v2 cycle failed; retrying: {type(error).__name__}: {error}", flush=True)
            time.sleep(max(0, interval - (time.monotonic() - started)))
    finally:
        for capture in captures.values():
            capture.release()


if __name__ == "__main__":
    main()
