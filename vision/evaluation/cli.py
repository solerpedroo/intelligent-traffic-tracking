"""Local evaluation entrypoint. An unfrozen split cannot be labeled as a benchmark."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from vision.contracts.errors import VisionError
from vision.datasets.ground_truth import GroundTruthSequence, SplitRegistry
from vision.datasets.predictions import (
    crossing_events,
    detection_boxes,
    load_predictions,
    observed_tracks,
)
from vision.evaluation.protocol import EvaluationProtocol
from vision.evaluation.report import block_reason, build_report


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="evaluate", description="Score one sequence from pipeline exports"
    )
    command.add_argument("--ground-truth", type=Path, required=True)
    command.add_argument("--predictions", type=Path, required=True)
    command.add_argument("--protocol", type=Path, required=True)
    command.add_argument("--splits", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--frame-rate", type=float, required=True)
    command.add_argument("--width", type=int, required=True)
    command.add_argument("--height", type=int, required=True)
    command.add_argument(
        "--allow-development",
        action="store_true",
        help="Score anyway and mark the report as not a frozen benchmark",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        sequence = GroundTruthSequence.model_validate_json(
            args.ground_truth.read_text(encoding="utf-8")
        )
        protocol = EvaluationProtocol.model_validate_json(args.protocol.read_text(encoding="utf-8"))
        registry = SplitRegistry.model_validate_json(args.splits.read_text(encoding="utf-8"))
        reason = block_reason(registry, sequence.sequence_id)
        claim = "frozen_test_benchmark"
        if reason is not None:
            if not args.allow_development:
                payload = {"error_code": reason, "benchmark_eligible": False}
                print(json.dumps(payload), file=sys.stderr)
                return 2
            claim = "development_not_benchmark"
        loaded = load_predictions(args.predictions)
        predictions = {
            "detections": None
            if loaded["detections"] is None
            else detection_boxes(loaded["detections"]),
            "events": None if loaded["events"] is None else crossing_events(loaded["events"]),
            "tracks": None,
        }
        if loaded["tracks"] is not None:
            predictions["tracks"], _excluded = observed_tracks(loaded["tracks"])
        report = build_report(
            sequence,
            predictions,
            protocol,
            timings=loaded["timings"],
            summary=loaded["summary"],
            mot_dir=args.output.parent / f"{args.output.stem}-mot",
            frame_rate=args.frame_rate,
            width=args.width,
            height=args.height,
            claim=claim,
        )
        if reason is not None:
            report["block_reason"] = reason
        args.output.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=2, allow_nan=False) + "\n"
        args.output.write_text(text, encoding="utf-8")
        print(json.dumps({"claim": report["claim"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, ValidationError, VisionError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {"error_code": getattr(error, "code", "invalid_input"), "error": str(error)}
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
