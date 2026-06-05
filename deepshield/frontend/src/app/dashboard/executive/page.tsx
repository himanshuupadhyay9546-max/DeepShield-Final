"use client";
/**
 * DeepShield Executive Dashboard
 * Real-time detection statistics, threat monitoring, risk scores,
 * fraud trend charts, and model performance cards.
 */
import { useState, useEffect, useCallback } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

// ── Types ──────────────────────────────────────────────────────────────────
interface DashboardStats {
  totalAnalyses: number;
  deepfakesDetected: number;
  authenticMedia: number;
  pendingAnalyses: number;
  avgConfidence: number;
  avgProcessingMs: number;
  apiCallsToday: number;
  activeUsers: number;
}

interface ThreatFeedItem {
  id: string;
  timestamp: string;
  verdict: "deepfake" | "authentic" | "uncertain";
  confidence: number;
  mediaType: "image" | "video" | "audio";
  orgName: string;
  riskScore: number;
}

interface ModelPerformance {
  name: string;
  accuracy: number;
  latencyMs: number;
  status: "healthy" | "degraded" | "down";
}

// ── Mock data ──────────────────────────────────────────────────────────────
const TREND_DATA = Array.from({ length: 30 }, (_, i) => ({
  day: `D${i + 1}`,
  deepfakes: Math.floor(Math.random() * 400 + 200),
  authentic: Math.floor(Math.random() * 600 + 400),
  uncertain: Math.floor(Math.random() * 80 + 20),
}));

const HOURLY_DATA = Array.from({ length: 24 }, (_, i) => ({
  hour: `${String(i).padStart(2, "0")}:00`,
  analyses: Math.floor(Math.random() * 300 + 50),
}));

const MODEL_STATS: ModelPerformance[] = [
  { name: "EfficientNet-B4",    accuracy: 97.95, latencyMs: 142, status: "healthy" },
  { name: "XceptionNet",        accuracy: 96.20, latencyMs: 168, status: "healthy" },
  { name: "ViT-Base/16",        accuracy: 95.80, latencyMs: 210, status: "healthy" },
  { name: "CNN+Transformer",    accuracy: 94.50, latencyMs: 195, status: "healthy" },
  { name: "Frequency Domain",   accuracy: 91.30, latencyMs: 85,  status: "healthy" },
];

const PIE_DATA = [
  { name: "Deepfake",  value: 23, color: "#A32D2D" },
  { name: "Authentic", value: 68, color: "#3B6D11" },
  { name: "Uncertain", value: 9,  color: "#BA7517" },
];

// ── Sub-components ──────────────────────────────────────────────────────────
function MetricCard({
  label, value, unit = "", trend, color = "blue",
}: {
  label: string; value: string | number; unit?: string;
  trend?: number; color?: "blue" | "green" | "red" | "amber";
}) {
  const colors = {
    blue:  { bg: "#E6F1FB", text: "#0C447C" },
    green: { bg: "#EAF3DE", text: "#27500A" },
    red:   { bg: "#FCEBEB", text: "#791F1F" },
    amber: { bg: "#FAEEDA", text: "#633806" },
  };
  const c = colors[color];
  return (
    <div style={{
      background: c.bg,
      borderRadius: 12,
      padding: "1rem 1.25rem",
      border: `0.5px solid ${c.text}30`,
    }}>
      <p style={{ fontSize: 12, color: c.text, margin: "0 0 4px", fontWeight: 500 }}>{label}</p>
      <p style={{ fontSize: 26, fontWeight: 500, margin: 0, color: c.text }}>
        {value}<span style={{ fontSize: 14, marginLeft: 2 }}>{unit}</span>
      </p>
      {trend !== undefined && (
        <p style={{ fontSize: 11, margin: "4px 0 0", color: trend >= 0 ? "#3B6D11" : "#A32D2D" }}>
          {trend >= 0 ? "▲" : "▼"} {Math.abs(trend).toFixed(1)}% vs yesterday
        </p>
      )}
    </div>
  );
}

function StatusDot({ status }: { status: ModelPerformance["status"] }) {
  const c = { healthy: "#3B6D11", degraded: "#BA7517", down: "#A32D2D" }[status];
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8,
      borderRadius: "50%", background: c, marginRight: 6,
    }} />
  );
}

// ── Main Dashboard ──────────────────────────────────────────────────────────
export default function ExecutiveDashboard() {
  const [stats] = useState<DashboardStats>({
    totalAnalyses:     1_847_293,
    deepfakesDetected:   423_104,
    authenticMedia:    1_398_821,
    pendingAnalyses:          47,
    avgConfidence:           0.962,
    avgProcessingMs:          187,
    apiCallsToday:         89_423,
    activeUsers:              3_204,
  });

  const [liveCount, setLiveCount] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setLiveCount(c => c + Math.floor(Math.random() * 3 + 1)), 800);
    return () => clearInterval(iv);
  }, []);

  const card: React.CSSProperties = {
    background: "var(--color-background-primary)",
    border: "0.5px solid var(--color-border-tertiary)",
    borderRadius: 12,
    padding: "1.25rem",
  };

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, margin: 0 }}>Executive dashboard</h1>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>
            Real-time deepfake threat intelligence
          </p>
        </div>
        <div style={{
          background: "#EAF3DE", color: "#27500A",
          padding: "6px 14px", borderRadius: 20, fontSize: 12, fontWeight: 500,
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <span style={{
            width: 7, height: 7, borderRadius: "50%", background: "#3B6D11",
            animation: "pulse 1.5s infinite",
          }} />
          Live · {(liveCount + stats.apiCallsToday).toLocaleString()} calls today
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: "1.5rem" }}>
        <MetricCard label="Total analyses" value={stats.totalAnalyses.toLocaleString()} trend={12.4} color="blue" />
        <MetricCard label="Deepfakes detected" value={stats.deepfakesDetected.toLocaleString()} trend={8.2} color="red" />
        <MetricCard label="Avg confidence" value={(stats.avgConfidence * 100).toFixed(1)} unit="%" trend={0.3} color="green" />
        <MetricCard label="Avg processing" value={stats.avgProcessingMs} unit="ms" trend={-5.1} color="amber" />
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: "1.5rem" }}>
        {/* 30-day trend */}
        <div style={card}>
          <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 1rem" }}>30-day detection trend</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={TREND_DATA} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-tertiary)" />
              <XAxis dataKey="day" tick={{ fontSize: 10 }} interval={4} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="deepfakes" stroke="#A32D2D" strokeWidth={2} dot={false} name="Deepfake" />
              <Line type="monotone" dataKey="authentic" stroke="#3B6D11" strokeWidth={2} dot={false} name="Authentic" />
              <Line type="monotone" dataKey="uncertain" stroke="#BA7517" strokeWidth={1.5} dot={false} name="Uncertain" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Verdict breakdown */}
        <div style={{ ...card, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 1rem", alignSelf: "flex-start" }}>Verdict breakdown</p>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={PIE_DATA} cx="50%" cy="50%" innerRadius={50} outerRadius={75} dataKey="value">
                {PIE_DATA.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => `${v}%`} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
            {PIE_DATA.map((d) => (
              <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: d.color }} />
                {d.name} {d.value}%
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Hourly volume */}
      <div style={{ ...card, marginBottom: "1.5rem" }}>
        <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 1rem" }}>Hourly analysis volume (today)</p>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={HOURLY_DATA} margin={{ top: 0, right: 20, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-tertiary)" />
            <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={3} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="analyses" fill="#185FA5" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Model performance table */}
      <div style={card}>
        <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 1rem" }}>AI model performance</p>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "0.5px solid var(--color-border-secondary)" }}>
              {["Model", "Accuracy", "Latency", "Status"].map(h => (
                <th key={h} style={{ padding: "6px 8px", textAlign: "left", fontWeight: 500, fontSize: 12, color: "var(--color-text-secondary)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MODEL_STATS.map((m, i) => (
              <tr key={m.name} style={{ borderBottom: "0.5px solid var(--color-border-tertiary)", background: i % 2 === 1 ? "var(--color-background-secondary)" : "transparent" }}>
                <td style={{ padding: "8px 8px", fontWeight: 500 }}>{m.name}</td>
                <td style={{ padding: "8px 8px", color: m.accuracy > 96 ? "#27500A" : "#BA7517" }}>
                  {m.accuracy.toFixed(2)}%
                </td>
                <td style={{ padding: "8px 8px" }}>{m.latencyMs}ms</td>
                <td style={{ padding: "8px 8px" }}>
                  <StatusDot status={m.status} />
                  {m.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
