"""Timing summaries from an existing run. Missing measurements stay null."""

import math


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil(fraction * len(ordered)) - 1
    return ordered[min(max(rank, 0), len(ordered) - 1)]


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _numbers(rows, key):
    if rows is None:
        return None
    return [float(row[key]) for row in rows]


def evaluate_performance(timings, summary):
    columns = (
        "decode_ms",
        "preprocessing_ms",
        "predict_ms",
        "inference_ms",
        "postprocessing_ms",
        "tracking_ms",
        "counting_ms",
        "analytics_ms",
        "render_ms",
        "encode_submit_ms",
    )
    stages = {}
    if timings is None:
        status = "not_evaluated"
        reason = "missing_timings"
    else:
        status = "evaluated"
        reason = None
        for key in columns:
            values = _numbers(timings, key)
            stages[key] = {
                "mean_ms": None if not values else sum(values) / len(values),
                "median_ms": _median(values),
                "p95_ms": _percentile(values, 0.95),
                "samples": 0 if values is None else len(values),
            }
    summary = summary or {}
    return {
        "status": status,
        "reason": reason,
        "stages": stages,
        "inference_fps": summary.get("inference_fps"),
        "end_to_end_fps": summary.get("end_to_end_fps"),
        "elapsed_s": summary.get("elapsed_s"),
        "ram_bytes": None,
        "vram_bytes": None,
        "resource_reason": "not_instrumented",
        "percentile": "nearest_rank_ceil",
    }
