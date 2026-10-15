"""JSON CLI boundary; model libraries and video extras are loaded only on demand."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from vision.contracts import ProcessingConfig


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="traffic-video", description="Local video input and export")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities", help="Report actual FFmpeg libraries and encoders")
    for name in ("probe", "process"):
        command = commands.add_parser(name)
        command.add_argument("input", type=Path)
        command.add_argument("--limits", type=Path, help="JSON override of VideoLimits")
        if name == "process":
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
        from vision.video import VideoError, VideoLimits, probe_video
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

                config = ProcessingConfig(
                    video_id=args.video_id, start_s=args.start_s, end_s=args.end_s
                )
                result = process_video(
                    args.input,
                    args.output_dir,
                    config=config,
                    limits=limits,
                    cfr_fallback_fps=args.cfr_fallback_fps,
                )
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except ModuleNotFoundError as error:
        if error.name not in {"av", "cv2"}:
            raise
        payload = {
            "error_code": "missing_video_extra",
            "error": "Install the project's video extra",
        }
    except (OSError, ValidationError, VideoError) as error:
        payload = {"error_code": getattr(error, "code", "invalid_input"), "error": str(error)}
    except KeyboardInterrupt:
        payload = {"error_code": "cancelled", "error": "Processing interrupted"}
        print(json.dumps(payload), file=sys.stderr)
        return 130
    print(json.dumps(payload), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
