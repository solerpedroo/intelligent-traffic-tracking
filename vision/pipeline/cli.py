"""JSON CLI boundary; model libraries and video extras are loaded only on demand."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from vision.contracts import AnalyticsConfig, ProcessingConfig
from vision.contracts.config import DetectorConfig, TrackerConfig
from vision.contracts.counting import CountingConfig
from vision.contracts.errors import VisionError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="traffic-video", description="Local video input and export")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities", help="Report actual FFmpeg libraries and encoders")
    commands.add_parser("models", help="List catalog definitions without loading models")
    prepare = commands.add_parser(
        "prepare-model", help="Explicitly download verified model weights"
    )
    prepare.add_argument("model_id")
    prepare.add_argument("--directory", type=Path, default=Path("checkpoints"))
    for name in ("probe", "process"):
        command = commands.add_parser(name)
        command.add_argument("input", type=Path)
        command.add_argument("--limits", type=Path, help="JSON override of VideoLimits")
        if name == "process":
            command.add_argument("--model", help="Catalog model ID; omitted means copy-only")
            command.add_argument("--checkpoint", type=Path, help="Local verified checkpoint")
            command.add_argument("--tracker", help="Catalog tracker preset ID")
            command.add_argument(
                "--tracker-config", type=Path, help="JSON override of TrackerConfig"
            )
            command.add_argument(
                "--counting-config", type=Path, help="CountingConfig JSON with normalized lines"
            )
            command.add_argument(
                "--analytics-config",
                type=Path,
                help="AnalyticsConfig JSON with normalized zones and heatmaps",
            )
            command.add_argument("--confidence", type=float)
            command.add_argument("--iou", type=float)
            command.add_argument("--image-size", type=int)
            command.add_argument("--classes", nargs="+")
            command.add_argument("--device")
            command.add_argument("--visualization-confidence", type=float)
            command.add_argument("--warmup-frames", type=int)
            command.add_argument("--threads", type=int)
            command.add_argument("--output-dir", type=Path, required=True)
            command.add_argument("--video-id", default="local-video")
            command.add_argument("--start-s", type=float, default=0.0)
            command.add_argument("--end-s", type=float)
            command.add_argument(
                "--cfr-fallback-fps",
                type=float,
                help="Explicit CFR assertion; overrides every input timestamp",
            )
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"models", "prepare-model"}:
            from vision.configs import load_catalog

            catalog = load_catalog()
            if args.command == "models":
                print(catalog.model_dump_json(indent=2))
            else:
                from vision.detectors.checkpoint import prepare_checkpoint

                model = catalog.get_model(args.model_id)
                path = prepare_checkpoint(model, args.directory)
                print(
                    json.dumps(
                        {
                            "model_id": model.model_id,
                            "checkpoint": str(path),
                            "sha256": model.checkpoint_sha256,
                        }
                    )
                )
            return 0
        from vision.video import VideoLimits, probe_video
        from vision.video.capabilities import video_capabilities

        if args.command == "capabilities":
            result = video_capabilities()
        else:
            limits = (
                VideoLimits.model_validate_json(args.limits.read_text())
                if args.limits
                else VideoLimits()
            )
            if args.command == "probe":
                result = probe_video(args.input, limits).model_dump(mode="json")
            else:
                from vision.pipeline.video import process_video

                options = {
                    name: getattr(args, name)
                    for name in (
                        "confidence",
                        "iou",
                        "image_size",
                        "device",
                        "visualization_confidence",
                        "warmup_frames",
                        "threads",
                    )
                    if getattr(args, name) is not None
                }
                if args.classes is not None:
                    options["classes"] = tuple(args.classes)
                if args.model is None and (options or args.checkpoint is not None):
                    raise VisionError("unsupported_config", "Detector options require --model")
                if args.tracker_config and not args.tracker:
                    raise VisionError("unsupported_config", "--tracker-config requires --tracker")
                tracker_config = TrackerConfig()
                if args.tracker:
                    from vision.configs import load_catalog

                    tracker_config = load_catalog().get_tracker(args.tracker).defaults
                if args.tracker_config:
                    overrides = json.loads(args.tracker_config.read_text())
                    if not isinstance(overrides, dict):
                        raise VisionError(
                            "invalid_input", "Tracker overrides must be a JSON object"
                        )
                    tracker_config = TrackerConfig.model_validate(
                        {**tracker_config.model_dump(mode="json"), **overrides}
                    )
                config = ProcessingConfig(
                    video_id=args.video_id,
                    start_s=args.start_s,
                    end_s=args.end_s,
                    detector_model_id=args.model,
                    tracker_config_id=args.tracker,
                    tracker=tracker_config,
                    detector=DetectorConfig(**options),
                    analytics=AnalyticsConfig.model_validate_json(args.analytics_config.read_text())
                    if args.analytics_config
                    else AnalyticsConfig(),
                    counting=CountingConfig.model_validate_json(args.counting_config.read_text())
                    if args.counting_config
                    else CountingConfig(),
                )
                result = process_video(
                    args.input,
                    args.output_dir,
                    config=config,
                    limits=limits,
                    cfr_fallback_fps=args.cfr_fallback_fps,
                    checkpoint=args.checkpoint,
                )
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except ModuleNotFoundError as error:
        if error.name not in {"av", "cv2", "torch", "ultralytics", "torchvision", "lap"}:
            raise
        payload = {
            "error_code": "missing_video_extra"
            if error.name in {"av", "cv2"}
            else "missing_detector_extra",
            "error": "Install the required video/detector extra",
        }
    except (OSError, ValueError, ValidationError, VisionError) as error:
        payload = {"error_code": getattr(error, "code", "invalid_input"), "error": str(error)}
    except KeyboardInterrupt:
        payload = {"error_code": "cancelled", "error": "Processing interrupted"}
        print(json.dumps(payload), file=sys.stderr)
        return 130
    print(json.dumps(payload), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
