"use client";

/**
 * Single-series time-series line chart.
 *
 * Mark specs: 2px round-join line, ~10%-opacity area wash, hairline solid
 * gridlines, 9px end-dot with a 2px surface ring, one selective direct
 * label at the line end. Hover: vertical crosshair snapping to the nearest
 * date with a tooltip; identical readout on keyboard focus (arrow keys).
 */

import {
  KeyboardEvent,
  PointerEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { theme } from "@/lib/theme";

export interface ChartPoint {
  date: Date;
  value: number;
}

interface Props {
  points: ChartPoint[];
  color: string;
  format: (value: number) => string;
  ariaLabel: string;
  height?: number;
}

const MARGIN = { top: 16, right: 76, bottom: 28, left: 56 };

function niceTicks(min: number, max: number, count = 4): number[] {
  if (min === max) {
    return [min];
  }
  const span = max - min;
  const step = Math.pow(10, Math.floor(Math.log10(span / count)));
  const error = (count * step) / span;
  const factor = error <= 0.15 ? 10 : error <= 0.35 ? 5 : error <= 0.75 ? 2 : 1;
  const niceStep = step * factor;
  const start = Math.ceil(min / niceStep) * niceStep;
  const ticks: number[] = [];
  for (let v = start; v <= max + 1e-12; v += niceStep) {
    ticks.push(Number(v.toPrecision(12)));
  }
  return ticks;
}

function formatDateTick(date: Date, spanDays: number): string {
  if (spanDays > 500) {
    return date.toLocaleDateString("en-US", { year: "numeric" });
  }
  if (spanDays > 120) {
    // "Jul ’25" — the apostrophe keeps it from reading as a day-of-month.
    const month = date.toLocaleDateString("en-US", { month: "short" });
    return `${month} ’${String(date.getFullYear()).slice(2)}`;
  }
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatDateFull(date: Date): string {
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function LineChart({
  points,
  color,
  format,
  ariaLabel,
  height = 260,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(720);
  const [active, setActive] = useState<number | null>(null);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      setWidth(Math.max(320, entries[0].contentRect.width));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const plot = useMemo(() => {
    if (points.length === 0) return null;
    const xs = points.map((p) => p.date.getTime());
    const values = points.map((p) => p.value);
    const xMin = xs[0];
    const xMax = xs[xs.length - 1];
    let vMin = Math.min(...values);
    let vMax = Math.max(...values);
    if (vMin === vMax) {
      vMin -= 1;
      vMax += 1;
    }
    const pad = (vMax - vMin) * 0.08;
    const yTicks = niceTicks(vMin - pad, vMax + pad);
    const yMin = Math.min(vMin - pad, yTicks[0]);
    const yMax = Math.max(vMax + pad, yTicks[yTicks.length - 1]);

    const innerW = width - MARGIN.left - MARGIN.right;
    const innerH = height - MARGIN.top - MARGIN.bottom;
    const x = (t: number) =>
      MARGIN.left + (xMax === xMin ? innerW / 2 : ((t - xMin) / (xMax - xMin)) * innerW);
    const y = (v: number) => MARGIN.top + innerH - ((v - yMin) / (yMax - yMin)) * innerH;

    const linePath = points
      .map((p, i) => `${i === 0 ? "M" : "L"}${x(p.date.getTime()).toFixed(2)},${y(p.value).toFixed(2)}`)
      .join("");
    const baselineY = MARGIN.top + innerH;
    const areaPath = `${linePath}L${x(xMax).toFixed(2)},${baselineY}L${x(xMin).toFixed(2)},${baselineY}Z`;

    const spanDays = (xMax - xMin) / 86_400_000;
    const xTickCount = Math.min(6, Math.max(2, Math.floor(innerW / 120)));
    const xTicks = Array.from({ length: xTickCount }, (_, i) => {
      const t = xMin + ((xMax - xMin) * i) / (xTickCount - 1 || 1);
      return { t, label: formatDateTick(new Date(t), spanDays) };
    });

    return { x, y, linePath, areaPath, yTicks, xTicks, baselineY, innerW };
  }, [points, width, height]);

  if (!plot || points.length === 0) {
    return (
      <div
        ref={containerRef}
        style={{ height, display: "grid", placeItems: "center", color: theme.inkMuted }}
      >
        No data yet — run “Update data”.
      </div>
    );
  }

  const nearestIndex = (clientX: number): number => {
    const rect = containerRef.current!.getBoundingClientRect();
    const px = clientX - rect.left;
    let best = 0;
    let bestDist = Infinity;
    for (let i = 0; i < points.length; i++) {
      const d = Math.abs(plot.x(points[i].date.getTime()) - px);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    }
    return best;
  };

  const onPointerMove = (event: PointerEvent<SVGSVGElement>) =>
    setActive(nearestIndex(event.clientX));

  const onKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    if (event.key === "ArrowRight") {
      setActive((i) => Math.min((i ?? points.length - 1) + 1, points.length - 1));
      event.preventDefault();
    } else if (event.key === "ArrowLeft") {
      setActive((i) => Math.max((i ?? points.length - 1) - 1, 0));
      event.preventDefault();
    } else if (event.key === "Escape") {
      setActive(null);
    }
  };

  const last = points[points.length - 1];
  const endX = plot.x(last.date.getTime());
  const endY = plot.y(last.value);
  const activePoint = active !== null ? points[active] : null;
  const tooltipLeft =
    activePoint !== null
      ? Math.min(plot.x(activePoint.date.getTime()) + 12, width - 170)
      : 0;

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <svg
        role="img"
        aria-label={ariaLabel}
        width={width}
        height={height}
        tabIndex={0}
        onPointerMove={onPointerMove}
        onPointerLeave={() => setActive(null)}
        onKeyDown={onKeyDown}
        onBlur={() => setActive(null)}
        style={{ display: "block", outline: "none", touchAction: "none" }}
      >
        {/* horizontal hairline gridlines + y ticks */}
        {plot.yTicks.map((tick) => (
          <g key={tick}>
            <line
              x1={MARGIN.left}
              x2={width - MARGIN.right}
              y1={plot.y(tick)}
              y2={plot.y(tick)}
              stroke={theme.grid}
              strokeWidth={1}
            />
            <text
              x={MARGIN.left - 8}
              y={plot.y(tick) + 3.5}
              textAnchor="end"
              fontSize={11}
              fill={theme.inkMuted}
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {format(tick)}
            </text>
          </g>
        ))}
        {/* baseline */}
        <line
          x1={MARGIN.left}
          x2={width - MARGIN.right}
          y1={plot.baselineY}
          y2={plot.baselineY}
          stroke={theme.baseline}
          strokeWidth={1}
        />
        {/* x ticks */}
        {plot.xTicks.map(({ t, label }) => (
          <text
            key={t}
            x={plot.x(t)}
            y={height - 8}
            textAnchor="middle"
            fontSize={11}
            fill={theme.inkMuted}
          >
            {label}
          </text>
        ))}
        {/* area wash + line */}
        <path d={plot.areaPath} fill={color} fillOpacity={0.1} />
        <path
          d={plot.linePath}
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* crosshair */}
        {activePoint && (
          <g>
            <line
              x1={plot.x(activePoint.date.getTime())}
              x2={plot.x(activePoint.date.getTime())}
              y1={MARGIN.top}
              y2={plot.baselineY}
              stroke={theme.baseline}
              strokeWidth={1}
            />
            <circle
              cx={plot.x(activePoint.date.getTime())}
              cy={plot.y(activePoint.value)}
              r={4.5}
              fill={color}
              stroke={theme.surface}
              strokeWidth={2}
            />
          </g>
        )}
        {/* end dot with surface ring + selective direct label */}
        <circle cx={endX} cy={endY} r={4.5} fill={color} stroke={theme.surface} strokeWidth={2} />
        <text
          x={endX + 10}
          y={endY + 4}
          fontSize={12}
          fontWeight={600}
          fill={theme.inkSecondary}
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {format(last.value)}
        </text>
      </svg>
      {/* tooltip (HTML layer) */}
      {activePoint && (
        <div
          style={{
            position: "absolute",
            left: tooltipLeft,
            top: Math.max(plot.y(activePoint.value) - 56, 4),
            background: theme.page,
            border: `1px solid ${theme.border}`,
            borderRadius: 8,
            padding: "8px 10px",
            pointerEvents: "none",
            minWidth: 130,
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 600, color: theme.inkPrimary }}>
            <span
              style={{
                display: "inline-block",
                width: 12,
                height: 2,
                background: color,
                verticalAlign: "middle",
                marginRight: 6,
              }}
            />
            {format(activePoint.value)}
          </div>
          <div style={{ fontSize: 11, color: theme.inkMuted, marginTop: 2 }}>
            {formatDateFull(activePoint.date)}
          </div>
        </div>
      )}
    </div>
  );
}
