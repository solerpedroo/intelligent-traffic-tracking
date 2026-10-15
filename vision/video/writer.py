"""H.264/MP4 writer preserving presentation intervals, with bounded buffering."""

from fractions import Fraction
from pathlib import Path

import av

from vision.contracts import FramePacket
from vision.video.errors import VideoError

OUTPUT_TIME_BASE = Fraction(1, 90_000)


class VideoWriter:
    def __init__(
        self, path: Path, width: int, height: int, fps: float | None, *, end_s: float | None = None
    ) -> None:
        if width % 2 or height % 2:
            raise VideoError("unsupported_export", "H.264 yuv420p export requires even dimensions")
        self.path, self.width, self.height = path, width, height
        self.fps = fps or 25.0
        self.end_s = end_s
        self._container = None
        self._pending: FramePacket | None = None
        self.origin_s: float | None = None
        self._last_ticks = -1
        self._durations: dict[int, float] = {}
        self.frames_written = 0
        self.last_duration_source: str | None = None
        self._abandoned = False
        self.closed = True

    def __enter__(self):
        try:
            self._container = av.open(str(self.path), mode="w", format="mp4")
            self._stream = self._container.add_stream(
                "libx264", rate=Fraction(self.fps).limit_denominator(100_000)
            )
            self._stream.width, self._stream.height = self.width, self.height
            self._stream.pix_fmt = "yuv420p"
            self._stream.time_base = OUTPUT_TIME_BASE
            self._stream.codec_context.time_base = OUTPUT_TIME_BASE
            self._stream.codec_context.max_b_frames = 0
            self._stream.codec_context.thread_count = 1
            self._stream.options = {"preset": "veryfast", "crf": "18", "tune": "zerolatency"}
        except (av.error.FFmpegError, ValueError) as error:
            if self._container is not None:
                self._container.close()
            raise VideoError("encode_error", f"H.264 encoder unavailable: {error}") from error
        self.closed = False
        return self

    @property
    def abandoned(self) -> bool:
        return self._abandoned

    def abandon(self) -> None:
        """Keep the partial file and skip the final flush."""
        self._abandoned = True
        self._pending = None

    def _mux(self, packets):
        for packet in packets:
            if packet.pts is None or packet.time_base is None:
                raise VideoError(
                    "encode_error", "Encoder emitted a packet without presentation time"
                )
            key = round(packet.pts * packet.time_base / OUTPUT_TIME_BASE)
            duration = self._durations.pop(key)
            packet.duration = max(1, round(duration / packet.time_base))
            self._container.mux(packet)

    def _encode(self, packet: FramePacket, duration_s: float):
        if self.origin_s is None:
            self.origin_s = packet.timestamp_s
        ticks = round((packet.timestamp_s - self.origin_s) / OUTPUT_TIME_BASE)
        if ticks <= self._last_ticks:
            raise VideoError(
                "timestamp_precision", "Export timestamps collide at the 90 kHz time base"
            )
        frame = av.VideoFrame.from_ndarray(packet.pixels, format="bgr24")
        frame.pts, frame.time_base = ticks, OUTPUT_TIME_BASE
        self._durations[ticks] = duration_s
        try:
            self._mux(self._stream.encode(frame))
        except av.error.FFmpegError as error:
            raise VideoError("encode_error", f"Video encoding failed: {error}") from error
        self.frames_written += 1
        self._last_ticks = ticks

    def write(self, packet: FramePacket) -> None:
        if self.closed:
            raise VideoError("writer_state", "Writer must be open")
        if packet.pixels.shape[:2] != (self.height, self.width):
            raise VideoError("unsupported_geometry", "Export frame dimensions changed")
        if self._pending is not None:
            delta = packet.timestamp_s - self._pending.timestamp_s
            if delta <= 0:
                raise VideoError("invalid_pts", "Export timestamps must be strictly increasing")
            self._encode(self._pending, delta)
        self._pending = packet

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None and not self._abandoned and self._pending is not None:
                duration = self._pending.duration_s
                self.last_duration_source = (
                    "decoder" if duration is not None else "reported_fps_or_25"
                )
                duration = duration if duration is not None else 1 / self.fps
                if self.end_s is not None:
                    duration = min(duration, self.end_s - self._pending.timestamp_s)
                self._encode(self._pending, duration)
                self._mux(self._stream.encode())
                if self._durations:
                    raise VideoError("encode_error", "Encoder did not emit all submitted frames")
        except av.error.FFmpegError as error:
            raise VideoError("encode_error", f"Video encoding failed: {error}") from error
        finally:
            self._pending = None
            self.closed = True
            try:
                self._container.close()
            except av.error.FFmpegError as error:
                if exc_type is None and not self._abandoned:
                    raise VideoError("encode_error", f"Could not finalize MP4: {error}") from error
