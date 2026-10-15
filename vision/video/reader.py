"""Bounded local MP4 input with explicit PTS or user-declared CFR timing."""

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from fractions import Fraction
from math import isfinite
from pathlib import Path

import av
import numpy as np

from vision.contracts import FramePacket
from vision.video.errors import VideoError
from vision.video.models import VideoLimits, VideoMetadata

ALLOWED_CODECS = {"h264", "hevc", "mpeg4", "av1", "vp9"}


def validate_path(path: Path, limits: VideoLimits) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise VideoError("invalid_input", "Input must be an existing local file")
    if path.suffix.lower() != ".mp4":
        raise VideoError("unsupported_format", "Only local .mp4 files are supported")
    size = path.stat().st_size
    if size == 0 or size > limits.max_bytes:
        raise VideoError("size_limit", "Input is empty or exceeds max_bytes")
    with path.open("rb") as source:
        signature = source.read(12)
    if len(signature) < 12 or signature[4:8] != b"ftyp":
        raise VideoError("unsupported_format", "Input must contain an ISO-BMFF ftyp header")
    if signature[8:12] == b"qt  ":
        raise VideoError(
            "unsupported_format", "QuickTime input is not supported in the MP4 baseline"
        )
    return path


@contextmanager
def open_input(path: Path, limits: VideoLimits):
    """Only pass an already-open local file to FFmpeg; prohibit secondary protocols."""
    path = validate_path(path, limits)
    try:
        with (
            path.open("rb") as source,
            av.open(
                source,
                mode="r",
                format="mov",
                options={"protocol_whitelist": "file", "enable_drefs": "0"},
            ) as container,
        ):
            if len(container.streams.video) != 1:
                raise VideoError("stream_count", "Exactly one video stream is required")
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 1
            stream.codec_context.options = {"err_detect": "explode"}
            yield container, stream, path
    except av.error.FFmpegError as error:
        raise VideoError("decode_error", f"FFmpeg could not read the input: {error}") from error


def inspect_stream(container, stream, path: Path, limits: VideoLimits) -> VideoMetadata:
    width, height = stream.codec_context.width, stream.codec_context.height
    if width <= 0 or height <= 0 or width * height > limits.max_pixels:
        raise VideoError("resolution_limit", "Video dimensions are invalid or exceed max_pixels")
    if stream.codec_context.name not in ALLOWED_CODECS:
        raise VideoError("unsupported_codec", "Video codec is not supported by the baseline")
    if stream.sample_aspect_ratio not in (None, Fraction(1, 1)):
        raise VideoError("unsupported_geometry", "Non-square video pixels are not supported")
    if stream.time_base is None or stream.time_base <= 0:
        raise VideoError("invalid_time_base", "Video stream has no valid time base")
    # Decode checks frame.rotation too: MP4 rotation may live in frame side data.
    try:
        rotation = float(stream.metadata.get("rotate", "0"))
    except ValueError as error:
        raise VideoError("unsupported_geometry", "Invalid video rotation metadata") from error
    if rotation % 360 != 0:
        raise VideoError("unsupported_geometry", "Rotated video must be normalized before input")
    if stream.duration is not None:
        duration, source = float(stream.duration * stream.time_base), "stream"
    elif container.duration is not None:
        duration, source = container.duration / av.time_base, "container"
    else:
        duration, source = None, "unknown"
    if duration is not None and (not isfinite(duration) or duration <= 0):
        raise VideoError("invalid_duration", "Reported duration must be positive and finite")
    if duration is not None and duration > limits.max_duration_s:
        raise VideoError("duration_limit", "Reported video duration exceeds max_duration_s")
    fps = float(stream.average_rate) if stream.average_rate else None
    if fps is not None and (not isfinite(fps) or fps <= 0):
        fps = None
    frames = stream.frames or None
    if frames is not None and frames > limits.max_frames:
        raise VideoError("frame_limit", "Reported video frame count exceeds max_frames")
    return VideoMetadata(
        filename=path.name,
        size_bytes=path.stat().st_size,
        container=container.format.name,
        codec=stream.codec_context.name,
        width=width,
        height=height,
        reported_fps=fps,
        reported_frames=frames,
        reported_duration_s=duration,
        stream_time_base=(stream.time_base.numerator, stream.time_base.denominator),
        stream_start_s=float(stream.start_time * stream.time_base)
        if stream.start_time is not None
        else None,
        duration_source=source,
    )


def probe_video(path: Path, limits: VideoLimits | None = None) -> VideoMetadata:
    limits = limits or VideoLimits()
    with open_input(path, limits) as (container, stream, path):
        return inspect_stream(container, stream, path, limits)


class VideoReader:
    """One-pass context-managed reader. No seeking: original frame indices stay exact."""

    def __init__(
        self,
        path: Path,
        limits: VideoLimits | None = None,
        *,
        cfr_fallback_fps: float | None = None,
    ) -> None:
        self.path = path
        self.limits = limits or VideoLimits()
        if cfr_fallback_fps is not None and (
            isinstance(cfr_fallback_fps, bool)
            or not isfinite(cfr_fallback_fps)
            or cfr_fallback_fps <= 0
        ):
            raise VideoError("invalid_fps", "Explicit CFR fallback FPS must be positive and finite")
        self.fallback_fps = cfr_fallback_fps
        self.decoded_frames = 0
        self.timestamp_origin_s: float | None = None
        self.closed = True
        self._iterated = False

    def __enter__(self):
        self._context = open_input(self.path, self.limits)
        self._container, self._stream, self.path = self._context.__enter__()
        try:
            self.metadata = inspect_stream(self._container, self._stream, self.path, self.limits)
        except BaseException:
            self._context.__exit__(*sys.exc_info())
            raise
        self.closed = False
        return self

    def __exit__(self, *exc):
        self.closed = True
        return self._context.__exit__(*exc)

    def __iter__(self) -> Iterator[FramePacket]:
        if self.closed or self._iterated:
            raise VideoError("reader_state", "Reader must be open and can only be iterated once")
        self._iterated = True
        previous = -1.0
        origin = None
        try:
            for index, frame in enumerate(self._container.decode(self._stream)):
                if self.closed:
                    raise VideoError("reader_state", "Reader was closed during iteration")
                if index >= self.limits.max_frames:
                    raise VideoError("frame_limit", "Decoded video exceeds max_frames")
                if frame.is_corrupt:
                    raise VideoError("corrupt_frame", "Decoder reported a corrupted frame")
                if (frame.width, frame.height) != (self.metadata.width, self.metadata.height):
                    raise VideoError(
                        "unsupported_geometry", "Frame dimensions changed during decode"
                    )
                if frame.rotation % 360 != 0:
                    raise VideoError("unsupported_geometry", "Rotated video is not supported")
                if self.fallback_fps is not None:
                    timestamp = index / self.fallback_fps
                    source = "fps_fallback"
                    duration = 1 / self.fallback_fps
                else:
                    if frame.pts is None or frame.time_base is None:
                        raise VideoError(
                            "missing_pts", "Missing PTS; explicit CFR fallback is required"
                        )
                    absolute = frame.pts * frame.time_base
                    if origin is None:
                        origin = absolute
                        self.timestamp_origin_s = float(absolute)
                    timestamp = float(absolute - origin)
                    source = "pts"
                    duration = float(frame.duration * frame.time_base) if frame.duration else None
                if not isfinite(timestamp) or timestamp < 0 or timestamp <= previous:
                    raise VideoError(
                        "invalid_pts", "Frame timestamps must be finite and strictly increasing"
                    )
                if timestamp >= self.limits.max_duration_s:
                    raise VideoError("duration_limit", "Decoded video exceeds max_duration_s")
                if duration is not None and (not isfinite(duration) or duration <= 0):
                    raise VideoError(
                        "invalid_duration", "Frame duration must be positive and finite"
                    )
                if (
                    duration is not None
                    and timestamp + duration > self.limits.max_duration_s + 1e-6
                ):
                    raise VideoError("duration_limit", "Frame duration exceeds max_duration_s")
                self.decoded_frames += 1
                previous = timestamp
                pixels = np.ascontiguousarray(frame.to_ndarray(format="bgr24"))
                yield FramePacket(index, timestamp, pixels, source, duration)
            if self.decoded_frames == 0:
                raise VideoError("empty_video", "Video contains no decodable frames")
            if self.metadata.reported_frames is not None:
                if self.decoded_frames != self.metadata.reported_frames:
                    raise VideoError(
                        "truncated_video", "Decoded frame count differs from the container header"
                    )
        except av.error.FFmpegError as error:
            raise VideoError("decode_error", f"Frame decode failed: {error}") from error
