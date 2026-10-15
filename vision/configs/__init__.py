"""Packaged model definitions without loading weights or model libraries."""

from importlib.resources import files
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from vision.contracts.base import Contract, Identifier, NonNegativeInt, Sha256
from vision.contracts.config import DetectorConfig
from vision.contracts.errors import VisionError


class ClassDefinition(Contract):
    id: NonNegativeInt
    name: Annotated[str, Field(min_length=1)]


class CatalogModel(Contract):
    model_id: Identifier
    filename: Identifier
    checkpoint_sha256: Sha256
    size_bytes: Annotated[int, Field(gt=0)]
    download_url: str
    source_release: str
    implementation_version: str
    license: str
    license_url: str
    classes: tuple[ClassDefinition, ...]

    @model_validator(mode="after")
    def validate_mapping(self) -> Self:
        ids, names = [c.id for c in self.classes], [c.name for c in self.classes]
        if not ids or len(set(ids)) != len(ids) or len(set(names)) != len(names):
            raise ValueError("Model class IDs and names must be non-empty and unique")
        return self

    def resolve_classes(self, names: tuple[str, ...]) -> tuple[int, ...]:
        lookup = {c.name: c.id for c in self.classes}
        missing = set(names) - lookup.keys()
        if missing:
            raise VisionError("invalid_classes", f"Unsupported model classes: {sorted(missing)}")
        return tuple(lookup[name] for name in names)


class ModelCatalog(Contract):
    schema_version: Literal["1.0"] = "1.0"
    models: tuple[CatalogModel, ...] = ()
    tracker_configs: tuple[()] = ()
    detector_defaults: DetectorConfig = Field(default_factory=DetectorConfig)

    @model_validator(mode="after")
    def validate_ids(self) -> Self:
        ids = [model.model_id for model in self.models]
        if len(set(ids)) != len(ids):
            raise ValueError("Model IDs must be unique")
        return self

    def get_model(self, model_id: str) -> CatalogModel:
        for model in self.models:
            if model.model_id == model_id:
                return model
        raise VisionError("unknown_model", f"Unknown catalog model: {model_id}")


def load_catalog() -> ModelCatalog:
    return ModelCatalog.model_validate_json(files(__package__).joinpath("catalog.json").read_text())
