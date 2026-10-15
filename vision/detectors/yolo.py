"""Verified local YOLO baseline; no HTTP imports or implicit asset downloads."""

import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter

import numpy as np

from vision.configs import CatalogModel
from vision.contracts import Detection
from vision.contracts.config import DetectorConfig
from vision.contracts.errors import VisionError
from vision.contracts.run import ModelReference
from vision.detectors.base import DetectionBatch
from vision.detectors.checkpoint import verify_checkpoint
from vision.detectors.geometry import LetterboxTransform


def normalize_detections(boxes, scores, classes, transform, allowed_ids):
    """Restore one canvas-to-original transform, clip, reject invalid predictions."""
    if not (len(boxes) == len(scores) == len(classes)):
        raise VisionError("invalid_predictions", "Mismatched detector output lengths")
    try:
        restored = transform.restore_boxes(boxes)
    except ValueError as error:
        raise VisionError("invalid_predictions", str(error)) from error
    result = []
    for box, score, class_id in zip(restored, scores, classes, strict=True):
        if not np.isfinite(score) or not 0 <= score <= 1:
            raise VisionError("invalid_predictions", "Invalid confidence from detector")
        if (
            not np.isfinite(class_id)
            or int(class_id) != class_id
            or int(class_id) not in allowed_ids
        ):
            raise VisionError("invalid_predictions", "Unexpected detector class")
        if box[2] <= box[0] or box[3] <= box[1]:
            continue  # Predictions entirely in padding have no original-image extent.
        result.append(
            Detection(
                bbox_xyxy=tuple(float(v) for v in box),
                class_id=int(class_id),
                confidence=float(score),
            )
        )
    return tuple(result)


class UltralyticsDetector:
    def __init__(self, model: CatalogModel, checkpoint: Path, config: DetectorConfig) -> None:
        started = perf_counter()
        checkpoint = verify_checkpoint(checkpoint, model)
        self.class_ids = model.resolve_classes(config.classes)
        try:
            installed_version = version("ultralytics-opencv-headless")
        except PackageNotFoundError as error:
            raise VisionError("missing_detector_extra", "Install the detector extra") from error
        if installed_version != model.implementation_version:
            raise VisionError(
                "implementation_mismatch", "Ultralytics version does not match catalog"
            )
        # These SDK settings apply to this local, single-model process, never user home.
        os.environ["YOLO_CONFIG_DIR"] = str(checkpoint.parent / ".ultralytics")
        os.environ["YOLO_OFFLINE"] = "true"
        os.environ["YOLO_AUTOINSTALL"] = "false"
        os.environ["YOLO_VERBOSE"] = "false"
        import torch
        from ultralytics import YOLO, settings

        settings.update({"sync": False})
        if config.device.startswith("cuda:"):
            index = int(config.device.split(":")[1])
            if not torch.cuda.is_available() or index >= torch.cuda.device_count():
                raise VisionError("device_unavailable", "Requested CUDA device is unavailable")
        torch.set_num_threads(config.threads)
        torch.manual_seed(config.seed)
        self._torch, self.config = torch, config
        self.class_names = {c.id: c.name for c in model.classes}
        try:
            self._model = YOLO(str(checkpoint), task="detect", verbose=False)
            self._model.to(config.device)
        except (RuntimeError, ValueError, OSError) as error:
            raise VisionError(
                "detector_load", f"Could not load verified YOLO checkpoint: {error}"
            ) from error
        if self._model.names != self.class_names:
            raise VisionError("class_mapping_mismatch", "Checkpoint classes do not match catalog")
        self.reference = ModelReference(
            model_id=model.model_id,
            checkpoint_sha256=model.checkpoint_sha256,
            implementation_version=model.implementation_version,
        )
        self.load_ms = (perf_counter() - started) * 1000
        self.warmup_ms = 0.0
        self._ready = False

    def _synchronize(self):
        if self.config.device.startswith("cuda:"):
            self._torch.cuda.synchronize(self.config.device)

    def _predict(self, canvas):
        try:
            self._synchronize()
            result = self._model.predict(
                source=canvas,
                imgsz=self.config.image_size,
                conf=self.config.confidence,
                iou=self.config.iou,
                classes=list(self.class_ids),
                device=self.config.device,
                rect=False,
                half=False,
                batch=1,
                max_det=self.config.max_detections,
                augment=False,
                verbose=False,
                save=False,
                stream=False,
            )[0]
            self._synchronize()
        except (RuntimeError, ValueError, OSError) as error:
            raise VisionError("detector_inference", f"YOLO inference failed: {error}") from error
        if tuple(result.orig_shape) != canvas.shape[:2]:
            raise VisionError("invalid_predictions", "SDK returned an unexpected coordinate frame")
        return result

    def warm_up(self, pixels):
        if self._ready:
            return
        transform = LetterboxTransform.for_shape(*pixels.shape[:2], self.config.image_size)
        canvas = transform.apply(pixels)
        started = perf_counter()
        for _ in range(self.config.warmup_frames):
            self._predict(canvas)
        self.warmup_ms = (perf_counter() - started) * 1000
        self._ready = True

    def detect(self, pixels) -> DetectionBatch:
        if not self._ready:
            raise VisionError("detector_not_ready", "Warm up before measuring inference")
        started = perf_counter()
        transform = LetterboxTransform.for_shape(*pixels.shape[:2], self.config.image_size)
        canvas = transform.apply(pixels)
        pre_ms = (perf_counter() - started) * 1000
        started = perf_counter()
        result = self._predict(canvas)
        predict_ms = (perf_counter() - started) * 1000
        started = perf_counter()
        data = result.boxes.data.detach().cpu().numpy()
        detections = normalize_detections(
            data[:, :4], data[:, 4], data[:, 5], transform, set(self.class_ids)
        )
        post_ms = (perf_counter() - started) * 1000
        inference_ms = float(result.speed["inference"])
        if not np.isfinite(inference_ms) or inference_ms < 0:
            raise VisionError("invalid_timing", "SDK returned invalid inference timing")
        return DetectionBatch(detections, pre_ms, predict_ms, post_ms, inference_ms)
