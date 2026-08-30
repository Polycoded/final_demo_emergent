"""Resilient RTSP/file/camera edge worker with measured light/deep evidence."""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from urllib.request import Request, urlopen

import cv2

from .detectors import DetectorPair, occupancy_union
from .telemetry import read_nvidia_gpu
from .vision import OpenCvFeatureExtractor


def post(endpoint: str, api_key: str, payload: dict) -> dict:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-CAHMA-Key": api_key},
    )
    with urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise RuntimeError(f"Router rejected feature event: {response.status}")
        return json.loads(response.read())


def report_execution(
    endpoint: str,
    api_key: str,
    feed_id: str,
    call_id: str,
    inference_ms: float,
    error: str | None = None,
) -> None:
    base = endpoint.split("/v1/features", 1)[0]
    outcome = "failure" if error else "complete"
    request = Request(
        f"{base}/v1/deep/{feed_id}/{outcome}",
        data=json.dumps(
            {"call_id": call_id, "inference_ms": inference_ms, "error": error}
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-CAHMA-Key": api_key},
    )
    with urlopen(request, timeout=4):
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="CAHMA Edge source worker")
    parser.add_argument("--feed-id", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:8080/v1/features/coordinated"
    )
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--evidence", type=Path, default=Path("evidence.jsonl"))
    parser.add_argument("--deep-model", type=Path)
    parser.add_argument("--light-model", type=Path)
    args = parser.parse_args()
    source = int(args.source) if args.source.isdigit() else args.source
    file_source = not isinstance(source, int)
    extractor = OpenCvFeatureExtractor(args.feed_id)
    detectors = DetectorPair(
        str(args.deep_model) if args.deep_model else None,
        str(args.light_model) if args.light_model else None,
    )
    deep_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cahma-deep")
    previous_light_count: int | None = None
    interval, next_sample = 1 / args.sample_fps, 0.0
    while True:
        capture = cv2.VideoCapture(source)
        if not capture.isOpened():
            time.sleep(3)
            continue
        try:
            while True:
                now = time.monotonic()
                if now < next_sample:
                    time.sleep(next_sample - now)
                next_sample = max(next_sample + interval, time.monotonic())
                ok, frame = capture.read()
                if not ok:
                    break
                if file_source:
                    source_fps = capture.get(cv2.CAP_PROP_FPS) or args.sample_fps
                    for _ in range(max(0, round(source_fps / args.sample_fps) - 1)):
                        if not capture.grab():
                            break
                light = detectors.light.detect(frame)
                features = extractor.analyze(frame)
                features.person_count, features.confidence_mean = light.count, light.confidence_mean
                features.confidence_variance = light.confidence_variance
                features.occupancy_ratio = occupancy_union(
                    light.boxes_xyxy, frame.shape[1], frame.shape[0]
                )
                prior_light_count = (
                    light.count if previous_light_count is None else previous_light_count
                )
                features.count_delta = abs(light.count - prior_light_count)
                previous_light_count = light.count
                gpu = read_nvidia_gpu()
                features.accelerator_utilization = (
                    min(1.0, max(0.0, gpu.utilization_percent / 100.0))
                    if gpu.utilization_percent is not None
                    else 0.0
                )
                try:
                    receipt = post(
                        args.endpoint,
                        args.api_key,
                        features.model_dump(mode="json"),
                    )
                except Exception as error:  # noqa: BLE001 - keep edge feeds alive
                    print(
                        f"[{args.feed_id}] coordinator request failed; retrying: "
                        f"{type(error).__name__}: {error}",
                        flush=True,
                    )
                    time.sleep(1)
                    continue
                if receipt.get("selected"):
                    call_id = receipt["call_id"]
                    deep_started = time.perf_counter()
                    try:
                        deep = deep_executor.submit(detectors.deep.detect, frame.copy()).result(
                            timeout=3
                        )
                    except TimeoutError:
                        report_execution(
                            args.endpoint,
                            args.api_key,
                            args.feed_id,
                            call_id,
                            (time.perf_counter() - deep_started) * 1000,
                            "Deep detector exceeded the worker timeout",
                        )
                        continue
                    except Exception as error:  # noqa: BLE001 - every failure must release the lease
                        report_execution(
                            args.endpoint,
                            args.api_key,
                            args.feed_id,
                            call_id,
                            (time.perf_counter() - deep_started) * 1000,
                            f"{type(error).__name__}: {error}",
                        )
                        continue
                    evidence = {
                        "window": receipt["window_id"],
                        "call_id": call_id,
                        "feature": features.model_dump(mode="json"),
                        "teacher_disagreement": detectors.disagreement(light, deep),
                        "light_inference_ms": light.inference_ms,
                        "deep_inference_ms": deep.inference_ms,
                    }
                    with args.evidence.open("a", encoding="utf-8") as output:
                        output.write(json.dumps(evidence) + "\n")
                    report_execution(
                        args.endpoint,
                        args.api_key,
                        args.feed_id,
                        call_id,
                        deep.inference_ms,
                    )
        finally:
            capture.release()
        time.sleep(1)


if __name__ == "__main__":
    main()
