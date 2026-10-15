"""Opt-in real CPU checks. Missing assets fail explicitly, never download or skip."""

import os
import socket
from pathlib import Path

import cv2
import numpy as np
import pytest

from vision.configs import load_catalog
from vision.contracts.config import DetectorConfig
from vision.detectors.yolo import UltralyticsDetector

pytestmark = pytest.mark.detector


@pytest.fixture(scope="module")
def detector():
    path = Path(os.environ.get("TRAFFIC_TEST_CHECKPOINT", "checkpoints/yolo11n.pt"))
    if not path.is_file():
        pytest.fail("Prepare checkpoint explicitly before running -m detector")
    with pytest.MonkeyPatch.context() as patch:

        def deny_network(*args, **kwargs):
            raise AssertionError("Inference must not open network connections")

        patch.setattr(socket.socket, "connect", deny_network)
        yield UltralyticsDetector(load_catalog().get_model("yolo11n-coco"), path, DetectorConfig())


@pytest.mark.parametrize("landscape", [False, True])
def test_real_cpu_detects_bus_and_keeps_original_coordinate_bounds(detector, landscape):
    path = Path(os.environ.get("TRAFFIC_TEST_IMAGE", "data/detector-smoke-bus.jpg"))
    image = cv2.imread(str(path))
    if image is None:
        pytest.fail("Provide the explicit official bus image for the integration smoke")
    if landscape:
        image = cv2.copyMakeBorder(
            image, 0, 0, 400, 400, cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )
    original = image.copy()
    detector.warm_up(image)
    result = detector.detect(image)
    assert any(item.class_id == 5 for item in result.detections)
    assert result.inference_ms > 0 and result.predict_ms >= result.inference_ms
    for detection in result.detections:
        x1, y1, x2, y2 = detection.bbox_xyxy
        assert 0 <= x1 < x2 <= image.shape[1]
        assert 0 <= y1 < y2 <= image.shape[0]
    np.testing.assert_array_equal(image, original)


def test_real_cpu_accepts_empty_detections(detector):
    image = np.zeros((96, 160, 3), dtype=np.uint8)
    detector.warm_up(image)
    assert detector.detect(image).detections == ()
