"use client";
/**
 * DeepShield — Animated Confidence Gauge
 * Circular SVG gauge showing fake probability + confidence score
 */
import { useEffect, useState } from "react";

interface Props {
  fakeProbability: number;   // 0–1
  confidence: number;        // 0–1
  verdict: "deepfake" | "authentic" | "uncertain";
  processingMs?: number;
}

const VERDICT_CFG = {
  deepfake:  { color: "#A32D2D", bg: "#FCEBEB", label: "DEEPFAKE",  emoji: "⚠️" },
  authentic: { color: "#3B6D11", bg: "#EAF3DE", label: "AUTHENTIC", emoji: "✅" },
  uncertain: { color: "#BA7517", bg: "#FAEEDA", label: "UNCERTAIN", emoji: "❓" },
};

export default function ConfidenceGauge({ fakeProbability, confidence, verdict, processingMs }: Props) {
  const [animated, setAnimated] = useState(0);
  const cfg = VERDICT_CFG[verdict];

  // Animate on mount
  useEffect(() => {
    let frame = 0;
    const target = fakeProbability * 100;
    const step = target / 40;
    const iv = setInterval(() => {
      frame++;
      setAnimated(prev => {
        const next = prev + step;
        if (next >= target) { clearInterval(iv); return target; }
        return next;
      });
    }, 18);
    return () => clearInterval(iv);
  }, [fakeProbability]);

  // SVG arc math
  const R = 70, CX = 90, CY = 90;
  const circumference = Math.PI * R; // half circle
  const pct = animated / 100;
  const dash = pct * circumference;
  const gap  = circumference - dash;

  return (
    <div style={{
      background: cfg.bg,
      border: `1px solid ${cfg.color}30`,
      borderRadius: 16,
      padding: "1.5rem",
      textAlign: "center",
      minWidth: 200,
    }}>
      {/* SVG half-circle gauge */}
      <svg width="180" height="100" viewBox="0 0 180 100">
        {/* Track */}
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          fill="none" stroke="#D3D1C7" strokeWidth="14" strokeLinecap="round"
        />
        {/* Fill */}
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          fill="none"
          stroke={cfg.color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${gap + 1}`}
          style={{ transition: "stroke-dasharray 0.05s" }}
        />
        {/* Center text */}
        <text x={CX} y={CY - 12} textAnchor="middle" fontSize="24" fontWeight="500" fill={cfg.color}>
          {animated.toFixed(0)}%
        </text>
        <text x={CX} y={CY + 8} textAnchor="middle" fontSize="11" fill="#73726C">
          fake probability
        </text>
      </svg>

      {/* Verdict badge */}
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        background: cfg.color, color: "#fff",
        borderRadius: 20, padding: "5px 14px",
        fontSize: 13, fontWeight: 500, marginBottom: 12,
      }}>
        {cfg.emoji} {cfg.label}
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {[
          { label: "Confidence", value: `${(confidence * 100).toFixed(1)}%` },
          { label: "Process time", value: processingMs ? `${processingMs}ms` : "—" },
        ].map(s => (
          <div key={s.label} style={{
            background: "rgba(255,255,255,0.5)", borderRadius: 8, padding: "8px 10px",
          }}>
            <p style={{ fontSize: 10, color: "#73726C", margin: "0 0 2px" }}>{s.label}</p>
            <p style={{ fontSize: 15, fontWeight: 500, margin: 0, color: cfg.color }}>{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
