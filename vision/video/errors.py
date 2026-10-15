"""Domain errors shared by the CLI and future worker."""

from vision.contracts.errors import VisionError


class VideoError(VisionError):
    """Video-specific expected failure."""
