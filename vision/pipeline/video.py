"""Streaming video processing shared by the CLI and future worker."""

import csv
import hashlib
import json
from collections import Counter
from contextlib import ExitStack, closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import cv2

from vision.configs import load_catalog
from vision.contracts import ProcessingConfig
from vision.contracts.errors import VisionError
from vision.contracts.run import ModelReference
from vision.detectors.base import DetectorAdapter
from vision.pipeline.manifest import make_manifest
from vision.video import VideoError, VideoLimits, VideoReader, VideoWriter, probe_video
from vision.video.capabilities import video_capabilities


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_video(
    input_path: Path,
    output_dir: Path,
    *,
    config: ProcessingConfig,
    limits: VideoLimits | None = None,
    cfr_fallback_fps: float | None = None,
    checkpoint: Path | None = None,
    detector: DetectorAdapter | None = None,
) -> dict:
    """Decode original indices, optionally detect, export [start_s,end_s).

    Models are loaded once per run. An injected adapter is a test/extension seam;
    its reference and mapping must match the selected catalog entry. Warm-up is
    excluded from per-frame inference statistics. No tracking or object counting.
    """
    started = perf_counter()
    input_path = input_path.expanduser().resolve()
    if config.tracker_config_id is not None:
        raise VideoError("unsupported_config", "Tracking is not available in Wave 2")
    if not config.render_annotated_video:
        raise VideoError("unsupported_config", "This pipeline requires video export")
    model = load_catalog().get_model(config.detector_model_id) if config.detector_model_id else None
    if model is not None:
        model.resolve_classes(config.detector.classes)
        if detector is None and checkpoint is None:
            raise VisionError("missing_checkpoint", "Provide a verified local checkpoint")
    elif detector is not None:
        raise VisionError("unsupported_config", "Injected detector requires a catalog model ID")
    limits = limits or VideoLimits()
    metadata = probe_video(input_path, limits)
    output_dir = output_dir.expanduser().resolve()
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise VideoError(
            "output_exists", "Output directory must be new; existing files are preserved"
        ) from error
    selected = 0
    first_s = last_s = None
    manifest = None
    observations = Counter()
    drawn_count = 0
    totals = dict.fromkeys(
        (
            "decode_ms",
            "preprocessing_ms",
            "predict_ms",
            "inference_ms",
            "postprocessing_ms",
            "render_ms",
            "encode_submit_ms",
        ),
        0.0,
    )
    try:
        write_json(output_dir / "metadata.json", metadata.model_dump(mode="json"))
        input_hash = sha256_file(input_path)
        write_json(
            output_dir / "config.json",
            {
                "schema_version": "1.0",
                "processing": config.model_dump(mode="json"),
                "limits": limits.model_dump(mode="json"),
                "timestamp_policy": "explicit_cfr"
                if cfr_fallback_fps is not None
                else "strict_pts",
                "cfr_fallback_fps": cfr_fallback_fps,
                "input_sha256": input_hash,
                "environment": video_capabilities(),
            },
        )
        if model is not None:
            reference = ModelReference(
                model_id=model.model_id,
                checkpoint_sha256=model.checkpoint_sha256,
                implementation_version=model.implementation_version,
            )
            manifest = make_manifest(
                uuid4().hex,
                config.video_id,
                input_hash,
                config,
                reference,
                config.detector.device,
                tuple((c.id, c.name) for c in model.classes),
            )
            write_json(output_dir / "manifest.json", manifest.model_dump(mode="json"))
            if detector is None:
                from vision.detectors.yolo import UltralyticsDetector

                detector = UltralyticsDetector(model, checkpoint, config.detector)
            if detector.reference != reference or detector.class_names != {
                c.id: c.name for c in model.classes
            }:
                raise VisionError(
                    "adapter_mismatch", "Adapter reference/mapping differs from catalog"
                )
        with VideoReader(input_path, limits, cfr_fallback_fps=cfr_fallback_fps) as reader:
            fps = cfr_fallback_fps or metadata.reported_fps
            with ExitStack() as stack:

                def csv_output(name, fields):
                    file = stack.enter_context(
                        (output_dir / (name + ".partial")).open("w", newline="", encoding="utf-8")
                    )
                    rows = csv.writer(file)
                    rows.writerow(fields)
                    return rows

                rows = csv_output(
                    "frames.csv",
                    ["frame_index", "timestamp_s", "timestamp_source", "export_timestamp_s"],
                )
                detection_rows = timing_rows = None
                if detector is not None:
                    detection_rows = csv_output(
                        "detections.csv",
                        [
                            "run_id",
                            "video_id",
                            "frame_index",
                            "timestamp_s",
                            "class_id",
                            "class_name",
                            "confidence",
                            "x1",
                            "y1",
                            "x2",
                            "y2",
                        ],
                    )
                    timing_rows = csv_output(
                        "timings.csv",
                        [
                            "frame_index",
                            "timestamp_s",
                            "decode_ms",
                            "preprocessing_ms",
                            "predict_ms",
                            "inference_ms",
                            "postprocessing_ms",
                            "render_ms",
                            "encode_submit_ms",
                        ],
                    )
                writer = stack.enter_context(
                    VideoWriter(
                        output_dir / "video.mp4.partial",
                        metadata.width,
                        metadata.height,
                        fps,
                        end_s=config.end_s,
                    )
                )
                frames = stack.enter_context(closing(iter(reader)))
                while True:
                    before = perf_counter()
                    try:
                        frame = next(frames)
                    except StopIteration:
                        break
                    decode_ms = (perf_counter() - before) * 1000
                    totals["decode_ms"] += decode_ms
                    if frame.frame_index == 0:
                        ok, encoded = cv2.imencode(".png", frame.pixels)
                        if not ok:
                            raise VideoError(
                                "preview_error", "Could not encode first-frame preview"
                            )
                        (output_dir / "preview.png.partial").write_bytes(encoded.tobytes())
                    if config.end_s is not None and frame.timestamp_s >= config.end_s:
                        break
                    if frame.timestamp_s < config.start_s:
                        continue
                    if first_s is None:
                        first_s = frame.timestamp_s
                    last_s = frame.timestamp_s
                    batch = None
                    render_ms = 0.0
                    output_frame = frame
                    if detector is not None:
                        from vision.rendering.detections import render_detections

                        if selected == 0:
                            detector.warm_up(frame.pixels)
                        batch = detector.detect(frame.pixels)
                        for item in batch.detections:
                            detection_rows.writerow(
                                [
                                    manifest.run_id,
                                    config.video_id,
                                    frame.frame_index,
                                    frame.timestamp_s,
                                    item.class_id,
                                    detector.class_names[item.class_id],
                                    item.confidence,
                                    *item.bbox_xyxy,
                                ]
                            )
                            observations[detector.class_names[item.class_id]] += 1
                        before = perf_counter()
                        pixels, drawn = render_detections(
                            frame.pixels,
                            batch.detections,
                            detector.class_names,
                            config.detector.visualization_confidence,
                        )
                        render_ms = (perf_counter() - before) * 1000
                        drawn_count += drawn
                        output_frame = replace(frame, pixels=pixels)
                        for key in (
                            "preprocessing_ms",
                            "predict_ms",
                            "inference_ms",
                            "postprocessing_ms",
                        ):
                            totals[key] += getattr(batch, key)
                        totals["render_ms"] += render_ms
                    before = perf_counter()
                    writer.write(output_frame)
                    encode_ms = (perf_counter() - before) * 1000
                    totals["encode_submit_ms"] += encode_ms
                    if batch is not None:
                        timing_rows.writerow(
                            [
                                frame.frame_index,
                                frame.timestamp_s,
                                decode_ms,
                                batch.preprocessing_ms,
                                batch.predict_ms,
                                batch.inference_ms,
                                batch.postprocessing_ms,
                                render_ms,
                                encode_ms,
                            ]
                        )
                    rows.writerow(
                        [
                            frame.frame_index,
                            frame.timestamp_s,
                            frame.timestamp_source,
                            frame.timestamp_s - first_s,
                        ]
                    )
                    selected += 1
                if selected == 0:
                    raise VideoError("empty_selection", "No frames fall in the selected interval")
            elapsed = perf_counter() - started
            summary = {
                "schema_version": "1.0",
                "status": "completed",
                "video_id": config.video_id,
                "selected_frames": selected,
                "decoded_frames": reader.decoded_frames,
                "first_source_timestamp_s": first_s,
                "last_source_timestamp_s": last_s,
                "timestamp_origin_s": reader.timestamp_origin_s,
                "timestamp_policy": "explicit_cfr"
                if cfr_fallback_fps is not None
                else "strict_pts",
                "input_validation": "selected_prefix"
                if config.end_s is not None
                else "full_decode",
                "export": {
                    "codec": "h264",
                    "pixel_format": "yuv420p",
                    "audio": False,
                    "time_base": [1, 90000],
                    "origin_s": first_s,
                    "last_frame_duration_source": writer.last_duration_source,
                },
                "elapsed_s": elapsed,
                "timing_scope": "pipeline_before_publication_including_load_and_warmup",
                "end_to_end_fps": selected / elapsed,
                "inference_fps": selected * 1000 / totals["inference_ms"]
                if totals["inference_ms"] > 0
                else None,
            }
            if detector is not None:
                summary["detector"] = {
                    "model_id": model.model_id,
                    "backend": type(detector).__name__,
                    "device": config.detector.device,
                    "class_observations": dict(observations),
                    "total_box_observations": sum(observations.values()),
                    "boxes_rendered": drawn_count,
                    "load_ms": detector.load_ms,
                    "warmup_ms": detector.warmup_ms,
                    "timing_totals": totals,
                    "mean_inference_ms": totals["inference_ms"] / selected,
                    "inference_timing_source": "SDK forward only; warm-up excluded",
                    "encode_timing_scope": "submit; final flush included only in elapsed_s",
                }
        names = ["video.mp4", "preview.png", "frames.csv"]
        if detector is not None:
            names += ["detections.csv", "timings.csv"]
        for name in names:
            (output_dir / f"{name}.partial").replace(output_dir / name)
        if manifest is not None:
            manifest = manifest.model_copy(update={"finished_at": datetime.now(UTC)})
            write_json(output_dir / "manifest.json", manifest.model_dump(mode="json"))
        write_json(output_dir / "summary.json", summary)
        return summary
    except (Exception, KeyboardInterrupt) as error:
        failure = {
            "status": "cancelled" if isinstance(error, KeyboardInterrupt) else "failed",
            "error_code": getattr(error, "code", type(error).__name__),
            "error": str(error) or "Processing interrupted",
            "selected_frames": selected,
            "final_artifacts_valid": False,
        }
        try:
            if manifest is not None:
                write_json(
                    output_dir / "manifest.json",
                    manifest.model_copy(update={"finished_at": datetime.now(UTC)}).model_dump(
                        mode="json"
                    ),
                )
            write_json(output_dir / "failure.json", failure)
        except OSError:
            pass
        raise
