"""Run the pre-specified A/B/C studies. Do not search for a better test score."""

import json
import subprocess
import sys
from pathlib import Path

from vision.datasets.ground_truth import GroundTruthSequence
from vision.datasets.predictions import detection_boxes, load_predictions
from vision.evaluation.degrade import (
    apply_degradation,
    frame_occupancy_bin,
    rewrite_video,
    sequence_density_bin,
)
from vision.evaluation.detection import evaluate_detection
from vision.evaluation.protocol import EvaluationProtocol
from vision.video import probe_video

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "experiments/configs/wave8-protocol.json"
SPLITS = ROOT / "experiments/configs/splits.json"
EVAL_PROTOCOL = ROOT / "experiments/configs/evaluation-protocol.json"
CHECKPOINT = ROOT / "checkpoints/yolo11n.pt"


def run(command):
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed


def process(video, output, video_id, tracker_config):
    summary = output / "summary.json"
    if summary.is_file():
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "vision.pipeline.cli",
        "process",
        str(video),
        "--model",
        "yolo11n-coco",
        "--checkpoint",
        str(CHECKPOINT),
        "--tracker",
        "bytetrack-default",
        "--tracker-config",
        str(tracker_config),
        "--video-id",
        video_id,
        "--output-dir",
        str(output),
        "--no-annotated-video",
    ]
    run(command)


def evaluate(sequence, predictions, output):
    if output.is_file():
        return json.loads(output.read_text())
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "scripts/evaluate.py",
        "--ground-truth",
        str(ROOT / sequence["ground_truth"]),
        "--predictions",
        str(predictions),
        "--protocol",
        str(EVAL_PROTOCOL),
        "--splits",
        str(SPLITS),
        "--output",
        str(output),
        "--frame-rate",
        str(sequence["frame_rate"]),
        "--width",
        str(sequence["width"]),
        "--height",
        str(sequence["height"]),
    ]
    if sequence["split"] != "test":
        command.append("--allow-development")
    run(command)
    return json.loads(output.read_text())


def tagged(report, study, condition, sequence_id):
    row = metrics(report)
    row.update(study=study, condition=condition, sequence_id=sequence_id)
    return row


def score_path(reports, condition, sequence):
    return reports / condition / f"{sequence['sequence_id']}.json"


def metrics(report):
    person = report["detection"]["operating_point_iou_0_5"]["0"]
    identity = report["mot"]["by_class"][0]
    return {
        "claim": report["claim"],
        "map_50_95": report["detection"]["mean_average_precision_50_95"],
        "precision_iou_0_5": person["precision"],
        "recall_iou_0_5": person["recall"],
        "hota": identity["HOTA"],
        "idf1": identity["IDF1"],
        "mota": identity["MOTA"],
        "idsw": identity["IDSW"],
        "inference_fps": report["performance"]["inference_fps"],
        "counting": report["counting"]["status"],
    }


def baseline_metrics(sequence):
    report_name = f"{sequence['sequence_id']}.json"
    report = json.loads((ROOT / "experiments/reports" / report_name).read_text())
    return metrics(report)


def write_tracker_config(path, overrides):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, indent=2) + "\n")


def degraded_video(sequence, condition):
    dest = ROOT / "artifacts/wave8/videos" / condition["id"] / f"{sequence['sequence_id']}.mp4"
    if dest.is_file():
        return dest
    source = ROOT / sequence["video"]
    kind = condition["kind"]
    if kind == "compression":
        rewrite_video(source, dest, None, crf=str(condition["crf"]))
    else:
        params = {key: value for key, value in condition.items() if key not in {"id", "kind"}}

        def transform(pixels, params=params, kind=kind):
            return apply_degradation(pixels, kind, **params)

        rewrite_video(source, dest, transform, crf="18")
    probed = probe_video(dest)
    if probed.reported_frames != probe_video(source).reported_frames:
        raise RuntimeError(f"{dest} changed the frame count")
    return dest


def occupancy(sequence, protocol):
    ground_truth = GroundTruthSequence.model_validate_json(
        (ROOT / sequence["ground_truth"]).read_text()
    )
    loaded = load_predictions(ROOT / sequence["baseline_predictions"])
    predictions = detection_boxes(loaded["detections"])
    length = probe_video(ROOT / sequence["video"]).reported_frames
    considered = [box for box in ground_truth.boxes if not box.ignore]
    density = len(considered) / length
    bins = protocol["experiment_b"]["sequence_bins"]
    by_frame = {}
    for box in considered:
        by_frame.setdefault(box.frame_index, 0)
        by_frame[box.frame_index] += 1
    grouped = {item["name"]: set() for item in protocol["experiment_b"]["frame_bins"]}
    for frame in range(length):
        name = frame_occupancy_bin(by_frame.get(frame, 0), protocol["experiment_b"]["frame_bins"])
        grouped[name].add(frame)
    strata = {}
    scoring = EvaluationProtocol()
    for name, frames in grouped.items():
        selected_truth = tuple(box for box in ground_truth.boxes if box.frame_index in frames)
        selected_predictions = [item for item in predictions if item["frame_index"] in frames]
        if not any(not box.ignore for box in selected_truth):
            strata[name] = {
                "status": "not_evaluated",
                "reason": "no_ground_truth",
                "frames": len(frames),
            }
            continue
        scored = evaluate_detection(selected_predictions, selected_truth, scoring)
        point = scored["operating_point_iou_0_5"]["0"]
        strata[name] = {
            "status": "evaluated",
            "frames": len(frames),
            "recall_iou_0_5": point["recall"],
            "precision_iou_0_5": point["precision"],
            "ground_truth": point["ground_truth"],
        }
    return {
        "objects_per_frame": density,
        "sequence_bin": sequence_density_bin(density, **bins),
        "occlusion": "not_evaluated",
        "occlusion_reason": "mot15_has_no_occlusion_flag",
        "frame_strata": strata,
    }


def svg(rows):
    width, height = 760, 40 + 22 * len(rows)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    maximum = max(row["hota"] for row in rows) or 1
    for index, row in enumerate(rows):
        y = 16 + index * 22
        bar = int(420 * row["hota"] / maximum)
        label = f"{row['study']} {row['condition']} {row['sequence_id']}"
        text = f'<text x="8" y="{y + 12}" font-size="11" font-family="sans-serif">{label}</text>'
        lines.append(text)
        lines.append(f'<rect x="320" y="{y}" width="{bar}" height="14" fill="#1d4e89"/>')
        value = f"{row['hota']:.3f}"
        score = f'<text x="{328 + bar}" y="{y + 12}" font-size="11">{value}</text>'
        lines.append(score)
    lines.append("</svg>")
    return "\n".join(lines)


def main():
    protocol = json.loads(PROTOCOL_PATH.read_text())
    work = ROOT / "artifacts/wave8"
    reports = work / "reports"
    default_config = work / "configs/baseline.json"
    write_tracker_config(default_config, {})
    table = []
    per_study = {"A": [], "B": [], "C": []}
    for sequence in protocol["sequences"]:
        base = baseline_metrics(sequence)
        base["study"] = "baseline"
        base["condition"] = "catalog-defaults"
        base["sequence_id"] = sequence["sequence_id"]
        table.append(base)
        for condition in protocol["experiment_a"]["conditions"]:
            config = work / "configs" / f"{condition['id']}.json"
            overrides = {key: value for key, value in condition.items() if key != "id"}
            write_tracker_config(config, overrides)
            output = work / "runs" / condition["id"] / sequence["sequence_id"]
            process(ROOT / sequence["video"], output, sequence["sequence_id"], config)
            report = evaluate(sequence, output, score_path(reports, condition["id"], sequence))
            row = tagged(report, "A", condition["id"], sequence["sequence_id"])
            table.append(row)
            per_study["A"].append(row)
        density = occupancy(sequence, protocol)
        per_study["B"].append(
            {"sequence_id": sequence["sequence_id"], "split": sequence["split"], **density}
        )
        for condition in protocol["experiment_c"]["conditions"]:
            video = degraded_video(sequence, condition)
            output = work / "runs" / condition["id"] / sequence["sequence_id"]
            process(video, output, sequence["sequence_id"], default_config)
            report = evaluate(sequence, output, score_path(reports, condition["id"], sequence))
            row = tagged(report, "C", condition["id"], sequence["sequence_id"])
            table.append(row)
            per_study["C"].append(row)
    summary = {
        "schema_version": "1.0",
        "protocol": "experiments/configs/wave8-protocol.json",
        "significance": "not_claimed",
        "counting": "not_evaluated_missing_crossing_events",
        "results": table,
        "density": per_study["B"],
    }
    destination = ROOT / "experiments/reports/wave8-summary.json"
    destination.write_text(json.dumps(summary, indent=2) + "\n")
    figure = ROOT / "experiments/reports/wave8-hota.svg"
    figure.write_text(svg([row for row in table if row["sequence_id"] == "MOT15-PETS09-S2L1"]))
    print(json.dumps({"summary": str(destination), "rows": len(table)}))


if __name__ == "__main__":
    main()
