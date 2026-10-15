"""Report the actual video libraries and baseline encoder capabilities."""

import shutil

import av
import cv2


def video_capabilities() -> dict:
    codecs = {}
    for name in ("libx264", "mpeg4", "png"):
        try:
            codecs[name] = av.Codec(name, "w").long_name
        except (av.error.FFmpegError, ValueError):
            codecs[name] = None
    return {
        "pyav_version": av.__version__,
        "opencv_version": cv2.__version__,
        "ffmpeg_libraries": {name: list(version) for name, version in av.library_versions.items()},
        "encoders": codecs,
        "system_ffmpeg": shutil.which("ffmpeg"),
        "system_ffprobe": shutil.which("ffprobe"),
        "requires_system_executables": False,
    }
