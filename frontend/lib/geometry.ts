export type DisplayPoint = { x: number; y: number };

export type FittedFrame = {
  offsetX: number;
  offsetY: number;
  drawnWidth: number;
  drawnHeight: number;
};

/** Map a container box to the original frame, including letterbox margins. */
export function fitContain(
  containerWidth: number,
  containerHeight: number,
  frameWidth: number,
  frameHeight: number,
): FittedFrame {
  if (
    containerWidth <= 0 ||
    containerHeight <= 0 ||
    frameWidth <= 0 ||
    frameHeight <= 0
  ) {
    return { offsetX: 0, offsetY: 0, drawnWidth: 0, drawnHeight: 0 };
  }
  const scale = Math.min(
    containerWidth / frameWidth,
    containerHeight / frameHeight,
  );
  const drawnWidth = frameWidth * scale;
  const drawnHeight = frameHeight * scale;
  return {
    offsetX: (containerWidth - drawnWidth) / 2,
    offsetY: (containerHeight - drawnHeight) / 2,
    drawnWidth,
    drawnHeight,
  };
}

/** Screen pixels are not frame pixels when the box has a margin. */
export function displayToNormalized(
  point: DisplayPoint,
  fit: FittedFrame,
): DisplayPoint | null {
  if (fit.drawnWidth <= 0 || fit.drawnHeight <= 0) return null;
  const x = (point.x - fit.offsetX) / fit.drawnWidth;
  const y = (point.y - fit.offsetY) / fit.drawnHeight;
  if (x < 0 || x > 1 || y < 0 || y > 1) return null;
  return { x, y };
}

export function normalizedToDisplay(
  point: DisplayPoint,
  fit: FittedFrame,
): DisplayPoint {
  return {
    x: fit.offsetX + point.x * fit.drawnWidth,
    y: fit.offsetY + point.y * fit.drawnHeight,
  };
}
