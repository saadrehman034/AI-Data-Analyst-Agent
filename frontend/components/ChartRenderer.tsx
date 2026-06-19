"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ChartType, ChartConfig } from "../lib/types";

const COLORS = [
  "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444",
  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
];

interface ChartRendererProps {
  chartType: ChartType;
  chartConfig: ChartConfig;
  data: Record<string, unknown>[];
  columns: string[];
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "number") {
    if (Number.isInteger(val)) return val.toLocaleString();
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (typeof val === "string" && /^-?\d+(\.\d+)?$/.test(val.trim())) {
    const num = parseFloat(val);
    if (!isNaN(num)) {
      if (Number.isInteger(num)) return num.toLocaleString();
      return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
  }
  return String(val);
}

function truncateLabel(label: string, maxLen = 15): string {
  return label.length > maxLen ? label.slice(0, maxLen) + "…" : label;
}

function formatAxisLabel(val: unknown): string {
  const str = String(val);
  // ISO date/datetime strings: YYYY-MM or YYYY-MM-DDTHH... → "Mon YYYY"
  if (/^\d{4}-\d{2}/.test(str)) {
    const d = new Date(str);
    if (!isNaN(d.getTime())) {
      return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    }
    // Plain YYYY-MM without time component
    const parts = str.slice(0, 7).split("-");
    if (parts.length === 2) {
      const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
      const m = parseInt(parts[1], 10) - 1;
      return `${monthNames[m] ?? parts[1]} ${parts[0]}`;
    }
  }
  return truncateLabel(str);
}

function NumberDisplay({ data, config }: { data: Record<string, unknown>[]; config: ChartConfig }) {
  const key = config.y_axis ?? (data[0] ? Object.keys(data[0])[0] : "");
  const val = data[0]?.[key];
  const title = config.title ?? (key ? String(key).replace(/_/g, " ") : "Result");

  return (
    <div className="flex flex-col items-center justify-center py-8">
      <p className="text-5xl font-bold text-blue-400 tabular-nums">
        {formatValue(val)}
      </p>
      <p className="mt-2 text-sm text-zinc-400 capitalize">{title}</p>
    </div>
  );
}

function TableDisplay({ data, columns }: { data: Record<string, unknown>[]; columns: string[] }) {
  const displayCols = columns.length > 0 ? columns : data.length > 0 ? Object.keys(data[0]) : [];

  return (
    <div className="overflow-auto max-h-72 rounded-lg border border-zinc-800">
      <table className="min-w-full text-xs">
        <thead className="sticky top-0 bg-zinc-900 border-b border-zinc-800">
          <tr>
            {displayCols.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left font-semibold text-zinc-400 whitespace-nowrap"
              >
                {col.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={i}
              className={i % 2 === 0 ? "bg-zinc-950" : "bg-zinc-900/50"}
            >
              {displayCols.map((col) => (
                <td
                  key={col}
                  className="px-3 py-2 text-zinc-300 whitespace-nowrap max-w-[200px] overflow-hidden text-ellipsis"
                >
                  {formatValue(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function coerceNumericStrings(rows: Record<string, unknown>[]): Record<string, unknown>[] {
  if (!rows.length) return rows;
  return rows.map((row) => {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(row)) {
      if (typeof v === "string" && /^-?\d+(\.\d+)?$/.test(v.trim())) {
        const n = parseFloat(v);
        out[k] = isNaN(n) ? v : n;
      } else {
        out[k] = v;
      }
    }
    return out;
  });
}

export function ChartRenderer({ chartType, chartConfig, data, columns }: ChartRendererProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-zinc-500">
        No data to display
      </div>
    );
  }

  const chartData = coerceNumericStrings(data);
  const xKey = chartConfig.x_axis ?? (columns[0] ?? Object.keys(data[0])[0]);
  const yKey = chartConfig.y_axis ?? (columns[1] ?? Object.keys(data[0])[1] ?? Object.keys(data[0])[0]);
  const title = chartConfig.title ?? "";

  const tooltipStyle = {
    backgroundColor: "#18181b",
    border: "1px solid #3f3f46",
    borderRadius: "8px",
    color: "#f4f4f5",
    fontSize: "12px",
  };

  if (chartType === "number") {
    return <NumberDisplay data={chartData} config={chartConfig} />;
  }

  if (chartType === "table") {
    return <TableDisplay data={data} columns={columns} />;
  }

  if (chartType === "bar") {
    return (
      <div>
        {title && <p className="mb-3 text-xs font-medium text-zinc-400 text-center">{title}</p>}
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 4, right: 16, left: 8, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey={xKey}
              tick={{ fill: "#a1a1aa", fontSize: 11 }}
              tickFormatter={(v) => formatAxisLabel(v)}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} tickFormatter={formatValue} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => [formatValue(v), yKey]} />
            <Bar dataKey={yKey} fill={COLORS[0]} radius={[4, 4, 0, 0]} maxBarSize={60} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (chartType === "line") {
    const sortedData = [...chartData].sort((a, b) => {
      const av = String(a[xKey] ?? ""), bv = String(b[xKey] ?? "");
      return av.localeCompare(bv);
    });
    return (
      <div>
        {title && <p className="mb-3 text-xs font-medium text-zinc-400 text-center">{title}</p>}
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={sortedData} margin={{ top: 4, right: 16, left: 8, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey={xKey}
              tick={{ fill: "#a1a1aa", fontSize: 11 }}
              tickFormatter={(v) => formatAxisLabel(v)}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} tickFormatter={formatValue} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => [formatValue(v), yKey]} />
            <Line
              type="monotone"
              dataKey={yKey}
              stroke={COLORS[0]}
              strokeWidth={2}
              dot={{ fill: COLORS[0], r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (chartType === "pie") {
    return (
      <div>
        {title && <p className="mb-3 text-xs font-medium text-zinc-400 text-center">{title}</p>}
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey={yKey}
              nameKey={xKey}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) =>
                `${truncateLabel(String(name), 12)} ${(percent * 100).toFixed(1)}%`
              }
              labelLine={false}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v) => [formatValue(v), yKey]}
            />
            <Legend
              formatter={(value) => (
                <span style={{ color: "#a1a1aa", fontSize: 11 }}>{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return <TableDisplay data={data} columns={columns} />;
}
