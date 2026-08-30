"""Derive three synchronized test feeds from the declared OpenCV fixture."""

import argparse
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("assets/scenarios"))
    parser.add_argument("--frames", type=int, default=180)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.source))
    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    width, height = (
        int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    codec = cv2.VideoWriter_fourcc(*"MJPG")
    writers = {
        "A": cv2.VideoWriter(str(args.output / "feed-a-clear.avi"), codec, fps, (width, height)),
        "B": cv2.VideoWriter(str(args.output / "feed-b-degraded.avi"), codec, fps, (width, height)),
        "C": cv2.VideoWriter(str(args.output / "feed-c-temporal.avi"), codec, fps, (width, height)),
    }
    index, previous = 0, None
    while index < args.frames:
        ok, frame = capture.read()
        if not ok:
            break
        small = cv2.resize(frame, (width // 4, height // 4), interpolation=cv2.INTER_AREA)
        degraded = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)
        degraded = cv2.GaussianBlur(degraded, (9, 9), 2.2)
        temporal = frame if index % 5 else (previous if previous is not None else frame)
        if index % 12 < 4:
            temporal = np.roll(temporal, 28, axis=1)
        writers["A"].write(frame)
        writers["B"].write(degraded)
        writers["C"].write(temporal)
        previous, index = frame, index + 1
    capture.release()
    for writer in writers.values():
        writer.release()
    print(f"Prepared {index} synchronized frames in {args.output}")


if __name__ == "__main__":
    main()
