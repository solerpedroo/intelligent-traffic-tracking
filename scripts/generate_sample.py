"""Generate original synthetic video fixtures; not real traffic or benchmark data."""

import argparse
import json
from fractions import Fraction
from pathlib import Path

import av
import numpy as np


def generate_sample(
    path: Path,
    *,
    profile: str = "cfr",
    frames: int = 24,
    width: int = 160,
    height: int = 96,
    origin_ms: int = 0,
) -> list[float]:
    if profile not in {"cfr", "vfr"} or frames < 1:
        raise ValueError("Choose cfr/vfr and at least one frame")
    if path.exists():
        raise FileExistsError("Sample output already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    intervals = [40 if profile == "cfr" else (40, 80, 120)[i % 3] for i in range(frames)]
    timestamps = [origin_ms]
    for delta in intervals[:-1]:
        timestamps.append(timestamps[-1] + delta)
    durations = dict(zip(timestamps, intervals, strict=True))
    with av.open(str(path), "w", format="mp4", options={"movflags": "+faststart"}) as container:
        stream = container.add_stream("libx264", rate=25)
        stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
        stream.time_base = stream.codec_context.time_base = Fraction(1, 1000)
        stream.codec_context.max_b_frames = 0
        stream.codec_context.thread_count = 1
        stream.options = {"crf": "0", "preset": "ultrafast", "tune": "zerolatency"}

        def mux(packets):
            for packet in packets:
                key = round(packet.pts * packet.time_base * 1000)
                packet.duration = round(Fraction(durations[key], 1000) / packet.time_base)
                container.mux(packet)

        for index, pts in enumerate(timestamps):
            pixels = np.full((height, width, 3), (24, 24, 24), dtype=np.uint8)
            pixels[height // 2 - 1 : height // 2 + 1, :] = (180, 180, 180)
            x = (index * 5) % max(1, width - 24)
            pixels[height // 3 : height // 3 + 16, x : x + 24] = (220, 70, 30)
            frame = av.VideoFrame.from_ndarray(pixels, format="bgr24")
            frame.pts, frame.time_base = pts, Fraction(1, 1000)
            mux(stream.encode(frame))
        mux(stream.encode())
    return [(value - origin_ms) / 1000 for value in timestamps]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", choices=("cfr", "vfr"), default="cfr")
    args = parser.parse_args()
    times = generate_sample(args.output, profile=args.profile)
    print(
        json.dumps(
            {
                "source": "original synthetic fixture",
                "profile": args.profile,
                "frame_timestamps_s": times,
                "license": "CC0-1.0",
            },
            indent=2,
        )
    )
