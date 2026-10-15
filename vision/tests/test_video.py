"""Real-codec integration plus injected faults for temporal and I/O boundaries."""

import csv
import json
import subprocess
import sys
from contextlib import closing, contextmanager
from fractions import Fraction
from types import SimpleNamespace

import av
import cv2
import numpy as np
import pytest

from scripts.generate_sample import generate_sample
from vision.contracts import FramePacket, ProcessingConfig
from vision.contracts.errors import VisionError
from vision.pipeline.video import process_video
from vision.video import VideoError, VideoLimits, VideoReader, VideoWriter, probe_video
from vision.video import reader as reader_module


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "input.mp4"
    generate_sample(path, frames=12)
    return path


def test_cfr_probe_decode_preview_and_round_trip(sample, tmp_path):
    meta = probe_video(sample)
    assert (meta.width, meta.height, meta.codec) == (160, 96, "h264")
    assert meta.reported_frames == 12
    assert meta.reported_fps == pytest.approx(25)
    assert meta.validation == "headers_only"
    output = tmp_path / "output"
    summary = process_video(sample, output, config=ProcessingConfig(video_id="test"))
    with VideoReader(sample) as source, VideoReader(output / "video.mp4") as result:
        originals, copies = list(source), list(result)
    assert [p.timestamp_s for p in copies] == pytest.approx([i / 25 for i in range(12)])
    assert len(copies) == summary["selected_frames"] == 12
    assert all(p.pixels.shape == (96, 160, 3) for p in copies)
    # Lossy YUV420/H.264 round-trip: allow 2% of the 8-bit range in mean error.
    assert np.abs(copies[0].pixels.astype(float) - originals[0].pixels).mean() < 255 * 0.02
    assert int(copies[0].pixels[36, 12, 0]) > int(copies[0].pixels[36, 12, 2]) + 100
    np.testing.assert_array_equal(cv2.imread(str(output / "preview.png")), originals[0].pixels)
    assert summary["inference_fps"] is None
    assert summary["input_validation"] == "full_decode"
    assert not list(output.glob("*.partial"))
    assert not (output / "failure.json").exists()


def test_vfr_uses_pts_and_export_preserves_irregular_intervals(tmp_path):
    path = tmp_path / "vfr.mp4"
    expected = generate_sample(path, profile="vfr", frames=12)
    with VideoReader(path) as source:
        observed = [p.timestamp_s for p in source]
    assert observed == pytest.approx(expected)
    assert len(set(round(b - a, 3) for a, b in zip(observed, observed[1:], strict=False))) == 3
    output = tmp_path / "output"
    process_video(path, output, config=ProcessingConfig(video_id="vfr"))
    with VideoReader(output / "video.mp4") as result:
        assert [p.timestamp_s for p in result] == pytest.approx(expected, abs=1 / 90000)
    assert probe_video(output / "video.mp4").reported_duration_s == pytest.approx(
        probe_video(path).reported_duration_s, abs=1 / 90000
    )


def test_segment_keeps_source_indices_origin_and_half_open_boundaries(tmp_path):
    path = tmp_path / "offset.mp4"
    expected = generate_sample(path, profile="vfr", frames=12, origin_ms=5000)
    output = tmp_path / "cut"
    summary = process_video(
        path,
        output,
        config=ProcessingConfig(
            video_id="clip",
            start_s=0.12,
            end_s=0.61,
        ),
    )
    rows = list(csv.DictReader((output / "frames.csv").read_text().splitlines()))
    selected = [(i, t) for i, t in enumerate(expected) if 0.12 <= t < 0.61]
    assert [int(row["frame_index"]) for row in rows] == [i for i, _ in selected]
    assert [float(row["timestamp_s"]) for row in rows] == [t for _, t in selected]
    assert summary["timestamp_origin_s"] == pytest.approx(5.0)
    assert summary["export"]["origin_s"] == 0.12
    with VideoReader(output / "video.mp4") as result:
        exported = list(result)
    assert [p.timestamp_s for p in exported] == pytest.approx([t - 0.12 for _, t in selected])
    assert probe_video(output / "video.mp4").reported_duration_s == pytest.approx(
        0.49, abs=1 / 90000
    )


def test_explicit_cfr_policy_overrides_entire_sequence_and_is_recorded(tmp_path):
    path = tmp_path / "vfr.mp4"
    generate_sample(path, profile="vfr", frames=6)
    with VideoReader(path, cfr_fallback_fps=25.0) as source:
        frames = list(source)
    assert [p.timestamp_s for p in frames] == pytest.approx([i / 25 for i in range(6)])
    assert all(p.timestamp_source == "fps_fallback" for p in frames)
    output = tmp_path / "fallback"
    summary = process_video(
        path, output, config=ProcessingConfig(video_id="cfr"), cfr_fallback_fps=25.0
    )
    assert summary["timestamp_policy"] == "explicit_cfr"
    assert json.loads((output / "config.json").read_text())["cfr_fallback_fps"] == 25


@pytest.mark.parametrize("fps", [0, -1, float("nan"), float("inf")])
def test_invalid_cfr_assertions_are_rejected(sample, fps):
    with pytest.raises(VideoError, match="positive and finite"):
        VideoReader(sample, cfr_fallback_fps=fps)


@pytest.mark.parametrize(
    "limits,code",
    [
        (VideoLimits(max_bytes=1), "size_limit"),
        (VideoLimits(max_pixels=100), "resolution_limit"),
        (VideoLimits(max_duration_s=0.1), "duration_limit"),
        (VideoLimits(max_frames=1), "frame_limit"),
    ],
)
def test_metadata_limits_are_enforced(sample, limits, code):
    with pytest.raises(VideoError) as raised:
        probe_video(sample, limits)
    assert raised.value.code == code


@pytest.mark.parametrize(
    "payload,code",
    [
        (b"", "size_limit"),
        (b"not really an mp4 file", "unsupported_format"),
        (b"\x00\x00\x00\x18ftypisomgarbage", "decode_error"),
    ],
)
def test_empty_disguised_and_corrupt_inputs_are_rejected(tmp_path, payload, code):
    path = tmp_path / "bad.mp4"
    path.write_bytes(payload)
    with pytest.raises(VideoError) as raised:
        probe_video(path)
    assert raised.value.code == code


def test_missing_path_and_unsupported_extension_are_rejected(sample, tmp_path):
    with pytest.raises(VideoError, match="existing local file"):
        probe_video(tmp_path / "missing.mp4")
    renamed = tmp_path / "input.avi"
    renamed.write_bytes(sample.read_bytes())
    with pytest.raises(VideoError, match="Only local .mp4"):
        probe_video(renamed)


def test_audio_only_mp4_is_not_a_video(tmp_path):
    path = tmp_path / "audio.mp4"
    with av.open(str(path), "w", format="mp4") as container:
        stream = container.add_stream("aac", rate=48000)
        frame = av.AudioFrame.from_ndarray(
            np.zeros((1, 1024), dtype=np.float32), format="fltp", layout="mono"
        )
        frame.sample_rate = 48000
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    with pytest.raises(VideoError) as raised:
        probe_video(path)
    assert raised.value.code == "stream_count"


def test_truncated_input_never_looks_like_a_successful_export(sample, tmp_path):
    truncated = tmp_path / "truncated.mp4"
    truncated.write_bytes(sample.read_bytes()[:-200])
    assert probe_video(truncated).reported_frames == 12  # Intact header, damaged media tail.
    output = tmp_path / "result"
    with pytest.raises(VideoError):
        process_video(truncated, output, config=ProcessingConfig(video_id="truncated"))
    assert not (output / "summary.json").exists()
    assert (output / "failure.json").exists()
    assert not (output / "video.mp4").exists()


def install_fake_frames(monkeypatch, sample, frames, limits=None):
    metadata = probe_video(sample)

    @contextmanager
    def fake_open(*args):
        yield SimpleNamespace(decode=lambda stream: iter(frames)), object(), sample

    monkeypatch.setattr(reader_module, "open_input", fake_open)
    monkeypatch.setattr(
        reader_module,
        "inspect_stream",
        lambda *args: metadata.model_copy(
            update={"reported_frames": None, "reported_duration_s": None},
        ),
    )
    return VideoReader(sample, limits)


def fake_frame(pts=0, **changes):
    data = {
        "pts": pts,
        "time_base": Fraction(1, 25),
        "duration": 1,
        "width": 160,
        "height": 96,
        "rotation": 0,
        "is_corrupt": False,
        "to_ndarray": lambda **kwargs: np.zeros((96, 160, 3), dtype=np.uint8),
    }
    return SimpleNamespace(**(data | changes))


@pytest.mark.parametrize(
    "frames,code",
    [
        ([fake_frame(None)], "missing_pts"),
        ([fake_frame(0), fake_frame(0)], "invalid_pts"),
        ([fake_frame(1), fake_frame(0)], "invalid_pts"),
        ([fake_frame(0, is_corrupt=True)], "corrupt_frame"),
        ([fake_frame(0, width=320)], "unsupported_geometry"),
        ([fake_frame(0, rotation=90)], "unsupported_geometry"),
        ([], "empty_video"),
    ],
)
def test_temporal_and_frame_faults_fail_explicitly(sample, monkeypatch, frames, code):
    reader = install_fake_frames(monkeypatch, sample, frames)
    with pytest.raises(VideoError) as raised, reader:
        list(reader)
    assert raised.value.code == code
    assert reader.closed


@pytest.mark.parametrize(
    "limits,frames,code",
    [
        (VideoLimits(max_frames=1), [fake_frame(0), fake_frame(1)], "frame_limit"),
        (VideoLimits(max_duration_s=0.1), [fake_frame(0), fake_frame(25)], "duration_limit"),
    ],
)
def test_decode_limits_apply_even_when_headers_do_not_report_duration(
    sample,
    monkeypatch,
    limits,
    frames,
    code,
):
    reader = install_fake_frames(monkeypatch, sample, frames, limits)
    with pytest.raises(VideoError) as raised, reader:
        list(reader)
    assert raised.value.code == code


def test_reader_context_closes_after_early_stop_and_rejects_reiteration(sample):
    with VideoReader(sample) as reader:
        with closing(iter(reader)) as frames:
            assert next(frames).frame_index == 0
        with pytest.raises(VideoError, match="only be iterated once"):
            next(iter(reader))
    assert reader.closed


@pytest.mark.parametrize(
    "failure", [VideoError("injected", "decode interrupted"), KeyboardInterrupt()]
)
def test_pipeline_preserves_partial_markers_and_closes_reader(
    sample, tmp_path, monkeypatch, failure
):
    original = VideoReader.__iter__
    readers = []

    def broken(self):
        readers.append(self)
        with closing(original(self)) as frames:
            yield next(frames)
            raise failure

    monkeypatch.setattr(VideoReader, "__iter__", broken)
    output = tmp_path / "interrupted"
    with pytest.raises(type(failure)):
        process_video(sample, output, config=ProcessingConfig(video_id="broken"))
    report = json.loads((output / "failure.json").read_text())
    assert report["final_artifacts_valid"] is False
    assert report["status"] == ("cancelled" if isinstance(failure, KeyboardInterrupt) else "failed")
    assert not (output / "summary.json").exists()
    assert not (output / "video.mp4").exists()
    assert readers[0].closed


def test_no_overwrite_and_empty_selection(sample, tmp_path):
    directory = tmp_path / "existing"
    directory.mkdir()
    sentinel = directory / "keep.txt"
    sentinel.write_text("keep")
    with pytest.raises(VideoError) as raised:
        process_video(sample, directory, config=ProcessingConfig(video_id="test"))
    assert raised.value.code == "output_exists"
    assert sentinel.read_text() == "keep"
    with pytest.raises(VideoError, match="No frames"):
        process_video(
            sample, tmp_path / "empty", config=ProcessingConfig(video_id="test", start_s=10.0)
        )


def test_cli_returns_json_and_useful_exit_codes(sample, tmp_path):
    command = [sys.executable, "-m", "vision.pipeline.cli"]
    probe = subprocess.run([*command, "probe", str(sample)], text=True, capture_output=True)
    assert probe.returncode == 0
    assert json.loads(probe.stdout)["codec"] == "h264"
    result = subprocess.run(
        [*command, "process", str(sample), "--output-dir", str(tmp_path / "cli")],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["selected_frames"] == 12
    invalid = subprocess.run(
        [
            *command,
            "process",
            str(sample),
            "--output-dir",
            str(tmp_path / "invalid"),
            "--start-s",
            "nan",
        ],
        text=True,
        capture_output=True,
    )
    assert invalid.returncode == 2
    assert json.loads(invalid.stderr)["error_code"] == "invalid_input"


@pytest.mark.parametrize("duration", [-1.0, 0.0, float("inf"), float("nan"), True])
def test_frame_duration_cannot_be_invalid(duration):
    with pytest.raises(ValueError, match="duration_s"):
        FramePacket(0, 0.0, np.zeros((2, 2, 3), dtype=np.uint8), duration_s=duration)


def test_writer_requires_even_dimensions(tmp_path):
    with pytest.raises(VideoError, match="even dimensions"):
        VideoWriter(tmp_path / "odd.mp4", 161, 96, 25.0)


def test_encoder_failure_is_explicit_and_writer_is_closed(tmp_path):
    def failed_encode(frame):
        raise av.error.InvalidDataError(1, "injected encoder failure")

    writer = VideoWriter(tmp_path / "failure.mp4", 160, 96, 25.0)
    with pytest.raises(VideoError) as raised, writer:
        writer._stream = SimpleNamespace(encode=failed_encode)
        pixels = np.zeros((96, 160, 3), dtype=np.uint8)
        writer.write(FramePacket(0, 0.0, pixels))
        writer.write(FramePacket(1, 0.04, pixels))
    assert raised.value.code == "encode_error"
    assert writer.closed


def test_pipeline_rejects_future_model_configuration(sample, tmp_path):
    with pytest.raises(VisionError, match="Unknown catalog model"):
        process_video(
            sample,
            tmp_path / "future",
            config=ProcessingConfig(
                video_id="test",
                detector_model_id="not-implemented",
            ),
        )
    assert not (tmp_path / "future").exists()
