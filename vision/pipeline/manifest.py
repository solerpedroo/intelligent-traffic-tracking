"""Capture installed versions and source provenance without importing model frameworks."""

import os
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from vision.contracts.run import RunManifest, SoftwareVersion, TrackerReference


def make_manifest(run_id, video_id, input_sha256, config, reference, device, class_mapping):
    def git(*args):
        try:
            result = subprocess.run(
                ["git", *args], text=True, capture_output=True, timeout=5, check=True
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    software = [SoftwareVersion(name="python", version=platform.python_version())]
    for name in (
        "intelligent-traffic-tracking",
        "numpy",
        "av",
        "opencv-python-headless",
        "torch",
        "torchvision",
        "lap",
        "ultralytics-opencv-headless",
    ):
        try:
            software.append(SoftwareVersion(name=name, version=version(name)))
        except PackageNotFoundError:
            pass
    processor = platform.processor()
    cpuinfo = Path("/proc/cpuinfo")
    if not processor and cpuinfo.is_file():
        try:
            for line in cpuinfo.read_text().splitlines():
                if line.startswith("model name"):
                    processor = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
    return RunManifest(
        run_id=run_id,
        video_id=video_id,
        input_sha256=input_sha256,
        config=config,
        started_at=datetime.now(UTC),
        git_commit=commit,
        git_dirty=status is None or bool(status),
        seed=config.detector.seed,
        hardware=(
            f"{platform.platform()}; {platform.machine()}; "
            f"processor={processor}; logical_cpus={os.cpu_count()}; device={device}"
        ),
        software=tuple(software),
        detector=reference,
        tracker=TrackerReference(tracker_config_id=config.tracker_config_id)
        if config.tracker_config_id
        else None,
        class_mapping=class_mapping,
    )
