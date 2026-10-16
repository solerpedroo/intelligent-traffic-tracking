"""Controlled visual degradations. Geometry and frame order stay unchanged."""

from fractions import Fraction
from pathlib import Path

import av
import cv2
import numpy as np

from vision.video import VideoReader, probe_video


def apply_degradation(pixels, kind, **params):
    if kind == "brightness":
        scaled = pixels.astype(np.float32) * float(params["scale"])
        return np.clip(scaled, 0, 255).astype(np.uint8)
    if kind == "blur":
        return cv2.GaussianBlur(pixels, (0, 0), float(params["sigma_px"]))
    if kind == "noise":
        generator = np.random.default_rng(int(params["seed"]))
        noise = generator.normal(0.0, float(params["sigma"]), pixels.shape)
        return np.clip(pixels.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    raise ValueError(f"Unsupported degradation: {kind}")


def sequence_density_bin(objects_per_frame, *, low_below, high_from):
    if objects_per_frame < low_below:
        return "low"
    if objects_per_frame >= high_from:
        return "high"
    return "medium"


def frame_occupancy_bin(count, bins):
    for item in bins:
        upper = item["max_objects"]
        if count >= item["min_objects"] and (upper is None or count <= upper):
            return item["name"]
    raise ValueError(f"No occupancy bin contains {count}")


def rewrite_video(source: Path, dest: Path, transform, *, crf: str = "18") -> int:
    """Write one output frame per decoded frame, in the same order."""
    metadata = probe_video(source)
    if metadata.reported_fps is None or metadata.reported_frames is None:
        raise ValueError("Degraded export needs a reported frame rate and length")
    dest.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(dest), "w")
    rate = Fraction(metadata.reported_fps).limit_denominator()
    stream = container.add_stream("libx264", rate=rate)
    stream.width, stream.height, stream.pix_fmt = metadata.width, metadata.height, "yuv420p"
    stream.options = {"preset": "veryfast", "crf": str(crf)}
    written = 0
    with VideoReader(source) as reader:
        for frame in reader:
            pixels = frame.pixels if transform is None else transform(frame.pixels)
            if pixels.shape != frame.pixels.shape:
                raise ValueError("Degradation changed the frame shape")
            packet = av.VideoFrame.from_ndarray(np.ascontiguousarray(pixels), format="bgr24")
            packet.pts = written
            for encoded in stream.encode(packet):
                container.mux(encoded)
            written += 1
    for encoded in stream.encode():
        container.mux(encoded)
    container.close()
    if written != metadata.reported_frames:
        raise ValueError(f"Wrote {written} frames, source reports {metadata.reported_frames}")
    return written
