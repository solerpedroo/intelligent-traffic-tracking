"""Explicit preparation and verification of allowlisted official weights."""

import hashlib
from pathlib import Path
from urllib.request import urlopen

from vision.configs import CatalogModel
from vision.contracts.errors import VisionError


def checkpoint_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checkpoint(path: Path, model: CatalogModel) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise VisionError("missing_checkpoint", "Prepare a local checkpoint before detection")
    if path.stat().st_size != model.size_bytes or checkpoint_hash(path) != model.checkpoint_sha256:
        raise VisionError(
            "checkpoint_mismatch", "Checkpoint size/SHA-256 does not match the catalog"
        )
    return path


def prepare_checkpoint(model: CatalogModel, directory: Path) -> Path:
    """Network access is restricted to this explicit operation, never inference."""
    directory = directory.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / model.filename
    if target.exists():
        return verify_checkpoint(target, model)
    if not model.download_url.startswith(
        "https://github.com/ultralytics/assets/releases/download/"
    ):
        raise VisionError("invalid_model_source", "Checkpoint source is not an official release")
    temporary = directory / (model.filename + ".partial")
    created = False
    try:
        with temporary.open("xb") as output:
            created = True
            with urlopen(model.download_url, timeout=60) as response:
                count = 0
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    count += len(chunk)
                    if count > model.size_bytes:
                        raise VisionError("checkpoint_mismatch", "Download exceeds catalog size")
                    output.write(chunk)
        verify_checkpoint(temporary, model)
        target.hardlink_to(temporary)  # Atomic no-clobber publication on the same filesystem.
        temporary.unlink()
        return target
    except BaseException:
        if created:
            temporary.unlink(missing_ok=True)
        raise
