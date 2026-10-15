"""One-to-one event matching on line, class, direction and a frozen time window."""

from collections import Counter


def _window(event, tolerance):
    return event.start_s - tolerance, event.end_s + tolerance


def match_events(predictions, ground_truth, tolerance_s):
    pairs = []
    for gt_index, event in enumerate(ground_truth):
        start, end = _window(event, tolerance_s)
        for pred_index, prediction in enumerate(predictions):
            if (
                prediction["line_id"] != event.line_id
                or prediction["class_id"] != event.class_id
                or prediction["direction"] != event.direction
            ):
                continue
            timestamp = prediction["timestamp_s"]
            if start <= timestamp <= end:
                pairs.append((abs(timestamp - event.start_s), gt_index, pred_index))
    used_gt, used_pred, matches = set(), set(), []
    for _, gt_index, pred_index in sorted(pairs):
        if gt_index in used_gt or pred_index in used_pred:
            continue
        used_gt.add(gt_index)
        used_pred.add(pred_index)
        matches.append((gt_index, pred_index))
    return matches


def _counts(events, key_of):
    return Counter(key_of(event) for event in events)


def evaluate_counting(predictions, ground_truth, protocol):
    ignored = set(protocol.ignored_class_ids)
    predictions = tuple(item for item in predictions if item["class_id"] not in ignored)
    ground_truth = tuple(item for item in ground_truth if item.class_id not in ignored)
    matches = match_events(predictions, ground_truth, protocol.counting_tolerance_s)
    true_positive = len(matches)
    false_positive = len(predictions) - true_positive
    false_negative = len(ground_truth) - true_positive

    def gt_key(event):
        return (event.line_id, event.class_id, event.direction)

    def pred_key(event):
        return (event["line_id"], event["class_id"], event["direction"])

    gt_counts = _counts(ground_truth, gt_key)
    pred_counts = _counts(predictions, pred_key)
    groups = []
    for key in sorted(set(gt_counts) | set(pred_counts)):
        gt_count = gt_counts[key]
        pred_count = pred_counts[key]
        absolute = abs(pred_count - gt_count)
        groups.append(
            {
                "line_id": key[0],
                "class_id": key[1],
                "direction": key[2],
                "ground_truth_count": gt_count,
                "predicted_count": pred_count,
                "absolute_error": absolute,
                "relative_error": None if gt_count == 0 else absolute / gt_count,
            }
        )
    gt_total = len(ground_truth)
    pred_total = len(predictions)
    absolute_total = abs(pred_total - gt_total)
    return {
        "status": "evaluated",
        "tolerance_s": protocol.counting_tolerance_s,
        "true_positives": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "precision": None
        if true_positive + false_positive == 0
        else true_positive / (true_positive + false_positive),
        "recall": None
        if true_positive + false_negative == 0
        else true_positive / (true_positive + false_negative),
        "empty_agreement": gt_total == 0 and pred_total == 0,
        "absolute_error": absolute_total,
        "relative_error": None if gt_total == 0 else absolute_total / gt_total,
        "groups": groups,
        "mean_absolute_error": None
        if not groups
        else sum(item["absolute_error"] for item in groups) / len(groups),
    }
