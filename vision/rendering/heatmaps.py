"""Export raw counts, mass-preserving Gaussian smoothing and display previews."""

from decimal import Decimal

import cv2
import numpy as np

from vision.contracts.errors import VisionError
from vision.pipeline.schemas import HEATMAP_INDEX_COLUMNS


def smooth_counts(raw, sigma_cells):
    values = raw.astype(np.float64)
    if sigma_cells == 0 or not values.any():
        return values
    radius = int(np.ceil(3 * sigma_cells))
    smoothed = cv2.GaussianBlur(
        values,
        (2 * radius + 1, 2 * radius + 1),
        sigma_cells,
        sigmaY=sigma_cells,
        borderType=cv2.BORDER_CONSTANT,
    )
    # Zero padding loses edge mass; preserve the recorded total after smoothing.
    return smoothed * (values.sum() / smoothed.sum())


def heatmap_preview(smoothed):
    peak = float(smoothed.max())
    if peak == 0:
        return np.zeros((*smoothed.shape, 3), dtype=np.uint8)
    scale = np.rint(smoothed / peak * 255).astype(np.uint8)
    preview = cv2.applyColorMap(scale, cv2.COLORMAP_INFERNO)
    preview[smoothed == 0] = 0
    return preview


class HeatmapWriter:
    fields = HEATMAP_INDEX_COLUMNS

    def __init__(self, directory, rows, config, run_id, video_id):
        self.directory, self.rows, self.config = directory, rows, config
        self.run_id, self.video_id = run_id, video_id
        self.warnings = []
        directory.mkdir(exist_ok=False)

    def __call__(self, bucket, grids):
        for class_id, raw in grids.items():
            stem = f"window-{bucket:08d}-class-{class_id}"
            smoothed = smooth_counts(raw, self.config.sigma_cells)
            with (self.directory / f"{stem}.npz").open("xb") as file:
                np.savez_compressed(file, raw=raw, smoothed=smoothed)
            preview_file = ""
            try:
                ok, encoded = cv2.imencode(".png", heatmap_preview(smoothed))
                if not ok:
                    raise VisionError("heatmap_export", "Could not encode heatmap preview")
                with (self.directory / f"{stem}.png").open("xb") as file:
                    file.write(encoded.tobytes())
                preview_file = f"heatmaps/{stem}.png"
            except (VisionError, cv2.error, OSError) as error:
                self.warnings.append(
                    {
                        "code": "heatmap_preview_failed",
                        "artifact": f"heatmaps/{stem}.png",
                        "message": str(error),
                    }
                )
            interval = Decimal(str(self.config.window_s))
            self.rows.writerow(
                [
                    self.run_id,
                    self.video_id,
                    float(bucket * interval),
                    float((bucket + 1) * interval),
                    class_id,
                    self.config.grid_width,
                    self.config.grid_height,
                    int(raw.sum()),
                    "observations_per_grid_cell",
                    self.config.sigma_cells,
                    f"heatmaps/{stem}.npz",
                    preview_file,
                ]
            )
