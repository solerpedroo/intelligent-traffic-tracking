"""Protocol locks and degradation geometry. They do not score the benchmark."""

import json
from pathlib import Path

import numpy as np

from scripts.generate_sample import generate_sample
from vision.evaluation.degrade import (
    apply_degradation,
    frame_occupancy_bin,
    rewrite_video,
    sequence_density_bin,
)
from vision.video import probe_video

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = json.loads((ROOT / "experiments/configs/wave8-protocol.json").read_text())


def test_wave8_factors_are_fixed_before_measurement():
    assert [item["id"] for item in PROTOCOL["experiment_a"]["conditions"]] == [
        "buffer-10",
        "buffer-60",
        "match-0.6",
        "match-0.9",
    ]
    assert PROTOCOL["experiment_b"]["sequence_bins"] == {"low_below": 5.0, "high_from": 8.0}
    assert PROTOCOL["experiment_b"]["occlusion"] == "not_available"
    assert [item["id"] for item in PROTOCOL["experiment_c"]["conditions"]] == [
        "brightness-0.6",
        "blur-sigma-1.5",
        "noise-sigma-15-seed-0",
        "noise-sigma-15-seed-1",
        "h264-crf-40",
    ]
    assert sequence_density_bin(4.7, low_below=5, high_from=8) == "low"
    assert sequence_density_bin(6.5, low_below=5, high_from=8) == "medium"
    assert frame_occupancy_bin(9, PROTOCOL["experiment_b"]["frame_bins"]) == "high"


def test_degradations_keep_shape_and_noise_is_repeatable():
    pixels = np.zeros((8, 8, 3), dtype=np.uint8)
    pixels[:] = 100
    dark = apply_degradation(pixels, "brightness", scale=0.6)
    assert dark.shape == pixels.shape and int(dark[0, 0, 0]) == 60
    blurred = apply_degradation(pixels, "blur", sigma_px=1.5)
    assert blurred.shape == pixels.shape
    first = apply_degradation(pixels, "noise", sigma=15, seed=0)
    second = apply_degradation(pixels, "noise", sigma=15, seed=0)
    other = apply_degradation(pixels, "noise", sigma=15, seed=1)
    assert np.array_equal(first, second)
    assert not np.array_equal(first, other)


def test_rewritten_video_keeps_every_frame(tmp_path):
    source = tmp_path / "source.mp4"
    generate_sample(source, frames=4, width=160, height=96)
    dest = tmp_path / "dark.mp4"
    written = rewrite_video(
        source, dest, lambda frame: apply_degradation(frame, "brightness", scale=0.6)
    )
    assert written == probe_video(dest).reported_frames == 4
