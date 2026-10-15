"""Packaged catalog; read-only and deliberately empty in Wave 0."""

from importlib.resources import files
from typing import Literal

from vision.contracts.base import Contract
from vision.contracts.run import ModelReference


class ModelCatalog(Contract):
    schema_version: Literal["1.0"] = "1.0"
    models: tuple[ModelReference, ...] = ()
    tracker_configs: tuple[()] = ()


def load_catalog() -> ModelCatalog:
    """Validate the packaged snapshot without network access or model imports."""
    return ModelCatalog.model_validate_json(files(__package__).joinpath("catalog.json").read_text())
