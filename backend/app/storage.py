"""Job files stay under the data directory. Download names are an allowlist."""

from pathlib import Path

ALLOWED_ARTIFACTS = frozenset(
    {
        "summary.json",
        "manifest.json",
        "config.json",
        "failure.json",
        "metadata.json",
        "frames.csv",
        "detections.csv",
        "timings.csv",
        "tracks.csv",
        "trajectories.csv",
        "track-lifetimes.csv",
        "crossing_events.csv",
        "crossing_windows.csv",
        "zone_events.csv",
        "zone_visits.csv",
        "zone_occupancy.csv",
        "heatmap_index.csv",
        "preview.png",
        "video.mp4",
    }
)


def video_dir(data_dir: Path, video_id: str) -> Path:
    return data_dir / "videos" / video_id


def job_dir(data_dir: Path, job_id: str) -> Path:
    return data_dir / "jobs" / job_id


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def artifact_path(directory: Path, name: str) -> Path | None:
    if name not in ALLOWED_ARTIFACTS or Path(name).name != name:
        return None
    candidate = (directory / name).resolve()
    if candidate.parent != directory.resolve() or not candidate.is_file():
        return None
    return candidate


def remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for item in sorted(path.rglob("*"), reverse=True):
        if item.is_file() or item.is_symlink():
            item.unlink()
        else:
            item.rmdir()
    path.rmdir()
