"""Wave 1 streaming copy pipeline with preview and auditable temporal mapping."""

import csv
import hashlib
import json
from contextlib import closing
from pathlib import Path
from time import perf_counter

import cv2

from vision.contracts import ProcessingConfig
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
) -> dict:
    """Process a selected [start_s,end_s) interval, decoding from original frame 0.

    A fresh output directory prevents clobbering previous runs. Header-only probe
    precedes output creation; later failures leave marked partials and failure.json.
    Partial-range runs do not claim validation of the undecoded tail of the input.
    """
    started = perf_counter()
    input_path = input_path.expanduser().resolve()
    if config.detector_model_id is not None or config.tracker_config_id is not None:
        raise VideoError("unsupported_config", "Detection and tracking are not available in Wave 1")
    if not config.render_annotated_video:
        raise VideoError("unsupported_config", "Wave 1 requires video export")
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
    try:
        write_json(output_dir / "metadata.json", metadata.model_dump(mode="json"))
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
                "input_sha256": sha256_file(input_path),
                "environment": video_capabilities(),
            },
        )
        with VideoReader(input_path, limits, cfr_fallback_fps=cfr_fallback_fps) as reader:
            fps = cfr_fallback_fps or metadata.reported_fps
            with (output_dir / "frames.csv.partial").open(
                "w", newline="", encoding="utf-8"
            ) as file:
                rows = csv.writer(file)
                rows.writerow(
                    ["frame_index", "timestamp_s", "timestamp_source", "export_timestamp_s"]
                )
                with VideoWriter(
                    output_dir / "video.mp4.partial",
                    metadata.width,
                    metadata.height,
                    fps,
                    end_s=config.end_s,
                ) as writer:
                    with closing(iter(reader)) as frames:
                        for frame in frames:
                            if frame.frame_index == 0:
                                ok, encoded = cv2.imencode(".png", frame.pixels)
                                if not ok:
                                    raise VideoError(
                                        "preview_error", "Could not encode the first-frame preview"
                                    )
                                (output_dir / "preview.png.partial").write_bytes(encoded.tobytes())
                            if config.end_s is not None and frame.timestamp_s >= config.end_s:
                                break
                            if frame.timestamp_s < config.start_s:
                                continue
                            if first_s is None:
                                first_s = frame.timestamp_s
                            last_s = frame.timestamp_s
                            writer.write(frame)
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
                            raise VideoError(
                                "empty_selection", "No frames fall in the selected interval"
                            )
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
                "timing_scope": "probe_hash_decode_preview_encode_csv_before_publication",
                "end_to_end_fps": selected / elapsed,
                "inference_fps": None,
            }
        for name in ("video.mp4", "preview.png", "frames.csv"):
            (output_dir / f"{name}.partial").replace(output_dir / name)
        write_json(output_dir / "summary.json", summary)
        return summary
    except (Exception, KeyboardInterrupt) as error:
        failure = {
            "status": "cancelled" if isinstance(error, KeyboardInterrupt) else "failed",
            "error_code": error.code if isinstance(error, VideoError) else type(error).__name__,
            "error": str(error) or "Processing interrupted",
            "selected_frames": selected,
            "final_artifacts_valid": False,
        }
        try:
            write_json(output_dir / "failure.json", failure)
        except OSError:
            pass  # Do not hide the original failure if storage is unavailable.
        raise
