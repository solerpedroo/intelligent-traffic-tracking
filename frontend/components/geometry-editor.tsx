"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { videoPreviewUrl } from "@/lib/api";
import {
  displayToNormalized,
  fitContain,
  normalizedToDisplay,
} from "@/lib/geometry";
import { type LineDraft, type ZoneDraft, zoneVertex } from "@/lib/job-draft";

type Mode = "line" | "zone";

export function GeometryEditor({
  videoId,
  previewReady,
  frameWidth,
  frameHeight,
  lines,
  zones,
  onChangeLine,
  onChangeZone,
}: {
  videoId: string;
  previewReady: boolean;
  frameWidth: number;
  frameHeight: number;
  lines: LineDraft[];
  zones: ZoneDraft[];
  onChangeLine: (index: number, line: LineDraft) => void;
  onChangeZone: (index: number, zone: ZoneDraft) => void;
}) {
  const stageRef = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ width: 0, height: 0 });
  const [mode, setMode] = useState<Mode>("line");
  const [lineIndex, setLineIndex] = useState(0);
  const [zoneIndex, setZoneIndex] = useState(0);
  const [lineEnd, setLineEnd] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const fit = fitContain(box.width, box.height, frameWidth, frameHeight);

  useLayoutEffect(() => {
    const node = stageRef.current;
    if (!node) return;
    const measure = () => {
      const rect = node.getBoundingClientRect();
      setBox({ width: rect.width, height: rect.height });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  function onStageClick(event: React.PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const point = displayToNormalized(
      { x: event.clientX - rect.left, y: event.clientY - rect.top },
      fitContain(rect.width, rect.height, frameWidth, frameHeight),
    );
    if (!point) {
      setNotice("That point is in the margin, not on the frame.");
      return;
    }
    setNotice(null);
    if (mode === "line" && lines[lineIndex]) {
      const current = lines[lineIndex];
      onChangeLine(
        lineIndex,
        lineEnd ? { ...current, end: point } : { ...current, start: point },
      );
      setLineEnd((value) => !value);
      return;
    }
    if (mode === "zone" && zones[zoneIndex]) {
      const current = zones[zoneIndex];
      onChangeZone(zoneIndex, {
        ...current,
        vertices: [...current.vertices, zoneVertex(point.x, point.y)],
      });
    }
  }

  return (
    <div className="editor">
      <fieldset>
        <legend>Drawing</legend>
        <label>
          <input
            type="radio"
            name="draw-mode"
            checked={mode === "line"}
            onChange={() => setMode("line")}
          />
          Line
        </label>
        <label>
          <input
            type="radio"
            name="draw-mode"
            checked={mode === "zone"}
            onChange={() => setMode("zone")}
          />
          Zone
        </label>
        <p id="direction-help">
          Side A is the negative cross-product side of start to end. On a
          left-to-right line, A is above and B is below. Swapping the endpoints
          swaps A and B.
        </p>
      </fieldset>
      <div
        ref={stageRef}
        className="stage"
        onPointerDown={onStageClick}
        aria-describedby="direction-help"
      >
        {previewReady ? (
          // The preview is a same-origin API image; fields remain the accessible edit path.
          // biome-ignore lint/performance/noImgElement: the frame is a dynamic API blob, not a static asset.
          <img
            src={videoPreviewUrl(videoId)}
            alt="First frame of the uploaded video"
          />
        ) : (
          <p>
            Preview frame is unavailable. Enter geometry with the numeric
            fields.
          </p>
        )}
        <svg
          aria-hidden="true"
          viewBox={`0 0 ${box.width || 1} ${box.height || 1}`}
        >
          {lines.map((line) => {
            const start = normalizedToDisplay(line.start, fit);
            const end = normalizedToDisplay(line.end, fit);
            return (
              <line
                key={line.lineId}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
              />
            );
          })}
          {zones.map((zone) => (
            <polygon
              key={zone.zoneId}
              points={zone.vertices
                .map((vertex) => {
                  const point = normalizedToDisplay(vertex, fit);
                  return `${point.x},${point.y}`;
                })
                .join(" ")}
            />
          ))}
        </svg>
      </div>
      {notice ? <p role="status">{notice}</p> : null}
      {lines.map((line, index) => (
        <fieldset key={line.lineId} className="geometry-fields">
          <legend>
            <label>
              <input
                type="radio"
                name="selected-line"
                checked={lineIndex === index}
                onChange={() => setLineIndex(index)}
              />
              Line {line.lineId}
            </label>
          </legend>
          <label>
            Line ID
            <input
              aria-label={`Line ID ${index + 1}`}
              value={line.lineId}
              onChange={(event) =>
                onChangeLine(index, { ...line, lineId: event.target.value })
              }
            />
          </label>
          <PointFields
            label="Start"
            point={line.start}
            onChange={(start) => onChangeLine(index, { ...line, start })}
          />
          <PointFields
            label="End"
            point={line.end}
            onChange={(end) => onChangeLine(index, { ...line, end })}
          />
        </fieldset>
      ))}
      {zones.map((zone, index) => (
        <fieldset key={zone.zoneId} className="geometry-fields">
          <legend>
            <label>
              <input
                type="radio"
                name="selected-zone"
                checked={zoneIndex === index}
                onChange={() => setZoneIndex(index)}
              />
              Zone {zone.zoneId}
            </label>
          </legend>
          <label>
            Zone ID
            <input
              aria-label={`Zone ID ${index + 1}`}
              value={zone.zoneId}
              onChange={(event) =>
                onChangeZone(index, { ...zone, zoneId: event.target.value })
              }
            />
          </label>
          {zone.vertices.map((vertex, vertexIndex) => (
            <PointFields
              key={vertex.id}
              label={`Vertex ${vertexIndex + 1}`}
              point={vertex}
              onChange={(next) => {
                const vertices = zone.vertices.slice();
                vertices[vertexIndex] = { ...vertex, ...next };
                onChangeZone(index, { ...zone, vertices });
              }}
            />
          ))}
        </fieldset>
      ))}
    </div>
  );
}

function PointFields({
  label,
  point,
  onChange,
}: {
  label: string;
  point: { x: number; y: number };
  onChange: (point: { x: number; y: number }) => void;
}) {
  return (
    <div className="point-fields">
      <label>
        {label} X
        <input
          aria-label={`${label} X`}
          type="number"
          min={0}
          max={1}
          step={0.01}
          value={point.x}
          onChange={(event) =>
            onChange({ ...point, x: Number(event.target.value) })
          }
        />
      </label>
      <label>
        {label} Y
        <input
          aria-label={`${label} Y`}
          type="number"
          min={0}
          max={1}
          step={0.01}
          value={point.y}
          onChange={(event) =>
            onChange({ ...point, y: Number(event.target.value) })
          }
        />
      </label>
    </div>
  );
}
