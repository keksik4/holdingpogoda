"use client";

import type { HourlyVisitorPoint } from "@/lib/types";
import { formatVisitors } from "@/lib/formatting";

interface HourlyVisitorsChartProps {
  data: HourlyVisitorPoint[];
  expectedTotal: number;
  selectedDateLabel: string;
  compact?: boolean;
}

export function HourlyVisitorsChart({ data, expectedTotal, selectedDateLabel, compact = false }: HourlyVisitorsChartProps) {
  const peak = data.reduce<HourlyVisitorPoint | null>((current, point) => (!current || point.expected_visitors > current.expected_visitors ? point : current), null);
  const peakHours = data.filter((point) => point.peak_hour_flag).map((point) => point.hour);
  const chart = buildChart(data);

  return (
    <section className="soft-panel p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-body text-[11px] font-semibold text-air-teal">Krzywa frekwencji</p>
          <h2 className="mt-1 font-display text-[20px] font-extrabold leading-none tracking-[-0.04em] text-ink">Prognoza godzinowa</h2>
        </div>
        <div className="flex items-center gap-3 font-body text-[10px] text-ink-soft">
          <span className="flex items-center gap-1.5"><span className="h-px w-6 bg-air-teal" />{selectedDateLabel}</span>
          <span className="flex items-center gap-1.5"><span className="h-px w-6 border-t border-dashed border-ink-soft/50" />Typowy dzień</span>
        </div>
      </div>

      <div className={compact ? "mt-2 h-[150px]" : "mt-2 h-[180px]"}>
        <svg viewBox="0 0 760 230" className="h-full w-full overflow-visible" role="img" aria-label="Prognoza liczby odwiedzających w kolejnych godzinach">
          {[0, 1, 2, 3].map((index) => {
            const y = 18 + index * 42;
            const label = Math.round(chart.maxValue - (chart.maxValue / 3) * index);
            return (
              <g key={index}>
                <path d={`M54 ${y}H744`} stroke="#dbe8f5" strokeWidth="1" strokeDasharray="3 6" />
                <text x="18" y={y + 4} fill="#58719a" fontSize="10" fontFamily="Aptos, Segoe UI, sans-serif">
                  {label >= 1000 ? `${Math.round(label / 1000)}K` : label}
                </text>
              </g>
            );
          })}
          <path d={chart.typicalPath} fill="none" stroke="#a6b8d1" strokeWidth="2" strokeDasharray="7 7" strokeLinecap="round" />
          <path d={chart.expectedPath} fill="none" stroke="#1264f5" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
          <path d={`${chart.expectedPath} L744 144 L54 144 Z`} fill="url(#chartFill)" opacity="0.13" />
          <defs>
            <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
              <stop stopColor="#1264f5" />
              <stop offset="1" stopColor="#1264f5" stopOpacity="0" />
            </linearGradient>
          </defs>
          {chart.points.map((point) => (
            <circle key={point.hour} cx={point.x} cy={point.y} r="2.6" fill="#1264f5" />
          ))}
          {chart.tickPoints.map((point) => (
            <text key={point.hour} x={point.x} y="202" textAnchor="middle" fill="#58719a" fontSize="10" fontFamily="Aptos, Segoe UI, sans-serif">
              {point.hour}:00
            </text>
          ))}
        </svg>
      </div>

      <div className="mt-1 grid grid-cols-3 divide-x divide-line rounded-[10px] bg-[#f7fafd] font-body text-ink">
        <SummaryMetric label="Szczyt" value={peakHours.length ? `${Math.min(...peakHours)}:00-${Math.max(...peakHours) + 1}:00` : "W trakcie"} />
        <SummaryMetric label="Godzina max" value={`~${formatVisitors(peak?.expected_visitors ?? 0)}`} />
        <SummaryMetric label="Suma dnia" value={formatVisitors(expectedTotal)} />
      </div>
    </section>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-3 py-2">
      <p className="text-[10px] text-ink-soft">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  );
}

function buildChart(data: HourlyVisitorPoint[]) {
  const width = 690;
  const height = 126;
  const left = 54;
  const top = 18;
  const maxValue = Math.max(100, Math.ceil(Math.max(...data.flatMap((point) => [point.expected_visitors, point.typical_visitors])) / 100) * 100);
  const toX = (index: number) => left + (data.length <= 1 ? 0 : (index / (data.length - 1)) * width);
  const toY = (value: number) => top + height - (value / maxValue) * height;
  const points = data.map((point, index) => ({ hour: point.hour, x: toX(index), y: toY(point.expected_visitors) }));
  const typicalPoints = data.map((point, index) => ({ hour: point.hour, x: toX(index), y: toY(point.typical_visitors) }));
  const tickPoints = points.filter((_, index) => index === 0 || index === points.length - 1 || index % 3 === 0);
  return { maxValue, points, tickPoints, expectedPath: toSmoothPath(points), typicalPath: toSmoothPath(typicalPoints) };
}

function toSmoothPath(points: Array<{ x: number; y: number }>) {
  if (!points.length) return "";
  if (points.length === 1) return `M${points[0].x} ${points[0].y}`;
  return points.reduce((path, point, index) => {
    if (index === 0) return `M${point.x} ${point.y}`;
    const previous = points[index - 1];
    const controlX = (previous.x + point.x) / 2;
    return `${path} C${controlX} ${previous.y}, ${controlX} ${point.y}, ${point.x} ${point.y}`;
  }, "");
}
