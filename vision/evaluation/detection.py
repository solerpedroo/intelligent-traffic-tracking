"""Class-wise detection scores. Boxes are matched inside one original frame."""


def box_iou(first, second) -> float:
    ax1, ay1, ax2, ay2 = first
    bx1, by1, bx2, by2 = second
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    if union <= 0:
        return 0.0
    return inter / union


def _area(box):
    x1, y1, x2, y2 = box
    return (x2 - x1) * (y2 - y1)


def scale_name(box):
    area = _area(box)
    if area < 32**2:
        return "small"
    if area < 96**2:
        return "medium"
    return "large"


def average_precision(matched_flags, ground_truth_count):
    """COCO 101-point interpolated AP. None when that class has no ground truth."""
    if ground_truth_count == 0:
        return None
    if not matched_flags:
        return 0.0
    true_positive = false_positive = 0
    curve = []
    for matched in matched_flags:
        if matched:
            true_positive += 1
        else:
            false_positive += 1
        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / ground_truth_count
        curve.append((recall, precision))
    total = 0.0
    for step in range(101):
        recall_level = step / 100
        precision = max((item[1] for item in curve if item[0] >= recall_level), default=0.0)
        total += precision
    return total / 101


def _match(predictions, ground_truth, threshold):
    ordered = sorted(enumerate(predictions), key=lambda item: (-item[1]["confidence"], item[0]))
    candidates = [box for box in ground_truth if not box.ignore]
    ignored = [box for box in ground_truth if box.ignore]
    used_candidates = set()
    used_ignored = set()
    flags = []
    for _, prediction in ordered:
        best = None
        for index, box in enumerate(candidates):
            if index in used_candidates:
                continue
            overlap = box_iou(prediction["bbox_xyxy"], box.bbox_xyxy)
            if overlap >= threshold and (best is None or overlap > best[0]):
                best = (overlap, index, False)
        if best is None:
            for index, box in enumerate(ignored):
                if index in used_ignored:
                    continue
                overlap = box_iou(prediction["bbox_xyxy"], box.bbox_xyxy)
                if overlap >= threshold and (best is None or overlap > best[0]):
                    best = (overlap, index, True)
        if best is None:
            flags.append(False)
        elif best[2]:
            used_ignored.add(best[1])
        else:
            used_candidates.add(best[1])
            flags.append(True)
    matched = len(used_candidates)
    return {
        "flags": flags,
        "true_positives": matched,
        "false_positives": flags.count(False),
        "false_negatives": len(candidates) - matched,
        "ground_truth": len(candidates),
    }


def _subset(predictions, ground_truth, class_id, scale=None):
    def keep(box, bbox):
        return box == class_id and (scale is None or scale_name(bbox) == scale)

    selected_predictions = [
        item for item in predictions if keep(item["class_id"], item["bbox_xyxy"])
    ]
    selected_truth = [item for item in ground_truth if keep(item.class_id, item.bbox_xyxy)]
    return selected_predictions, selected_truth


def _by_frame(predictions, ground_truth, threshold):
    frames = {item["frame_index"] for item in predictions}
    frames.update(item.frame_index for item in ground_truth)
    flags = []
    totals = {"true_positives": 0, "false_positives": 0, "false_negatives": 0, "ground_truth": 0}
    for frame in sorted(frames):
        result = _match(
            [item for item in predictions if item["frame_index"] == frame],
            [item for item in ground_truth if item.frame_index == frame],
            threshold,
        )
        flags.extend(result["flags"])
        for key in totals:
            totals[key] += result[key]
    return flags, totals


def _ratio(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def evaluate_detection(predictions, ground_truth, protocol, *, scale=None):
    classes = {
        item.class_id
        for item in ground_truth
        if not item.ignore and item.class_id not in protocol.ignored_class_ids
    }
    if scale is not None:
        classes = {
            class_id
            for class_id in classes
            if any(
                item.class_id == class_id
                and not item.ignore
                and scale_name(item.bbox_xyxy) == scale
                for item in ground_truth
            )
        }
    per_class = {}
    operating = {}
    for class_id in sorted(classes):
        selected_predictions, selected_truth = _subset(
            [item for item in predictions if item["class_id"] not in protocol.ignored_class_ids],
            [item for item in ground_truth if item.class_id not in protocol.ignored_class_ids],
            class_id,
            scale,
        )
        aps = []
        for threshold in protocol.detection_iou_thresholds:
            flags, totals = _by_frame(selected_predictions, selected_truth, threshold)
            aps.append(average_precision(flags, totals["ground_truth"]))
            if threshold == 0.5:
                positives = totals["true_positives"]
                operating[str(class_id)] = {
                    "precision": _ratio(positives, positives + totals["false_positives"]),
                    "recall": _ratio(positives, totals["ground_truth"]),
                    **totals,
                }
        if any(item is None for item in aps):
            per_class[str(class_id)] = None
        else:
            per_class[str(class_id)] = sum(aps) / len(aps)
    scored = [value for value in per_class.values() if value is not None]
    return {
        "status": "evaluated" if scored else "not_evaluated",
        "reason": None if scored else "no_detection_ground_truth",
        "scale": scale or "all",
        "mean_average_precision_50_95": None if not scored else sum(scored) / len(scored),
        "average_precision_by_class": per_class,
        "operating_point_iou_0_5": operating,
        "ignored_class_ids": list(protocol.ignored_class_ids),
    }
