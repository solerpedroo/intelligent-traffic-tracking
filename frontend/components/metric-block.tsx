import type { Metric } from "@/lib/analytics";

export function MetricNote({ metric }: { metric: Metric }) {
  if (metric.status === "measured" && !metric.reason) return null;
  return (
    <p role={metric.status === "not_evaluated" ? "status" : undefined}>
      {metric.status === "not_evaluated" ? "Not evaluated. " : ""}
      {metric.reason}
    </p>
  );
}

export function Bars({
  items,
  unit,
}: {
  items: { key: string; label: string; value: number }[];
  unit: string;
}) {
  const peak = Math.max(1, ...items.map((item) => item.value));
  if (items.length === 0) return <p>No rows in this export.</p>;
  return (
    <ul className="bars">
      {items.map((item) => (
        <li key={item.key}>
          <span>
            {item.label}: {item.value} {unit}
          </span>
          <span
            className="bar"
            style={{ width: `${(item.value / peak) * 100}%` }}
          />
        </li>
      ))}
    </ul>
  );
}
