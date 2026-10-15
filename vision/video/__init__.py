"""Optional local video adapters; install the video extra before importing."""

from vision.video.errors import VideoError
from vision.video.models import VideoLimits, VideoMetadata
from vision.video.reader import VideoReader, probe_video
from vision.video.writer import VideoWriter

__all__ = [
    "VideoError",
    "VideoLimits",
    "VideoMetadata",
    "VideoReader",
    "VideoWriter",
    "probe_video",
]
