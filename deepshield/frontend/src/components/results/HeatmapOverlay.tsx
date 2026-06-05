"use client";
/**
 * GradCAM Heatmap Overlay Viewer
 * Shows manipulation regions annotated over original image
 */
import { useState } from "react";

interface Region {
  x: number; y: number; w: number; h: number; score: number; label?: string;
}
interface Props {
  originalUrl: string;
  heatmapUrl:  string;
  regions?:    Region[];
  verdict:     "deepfake" | "authentic" | "uncertain";
}

export default function HeatmapOverlay({ originalUrl, heatmapUrl, regions = [], verdict }: Props) {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [opacity, setOpacity]         = useState(60);

  const verdictColor = { deepfake: "#A32D2D", authentic: "#3B6D11", uncertain: "#BA7517" }[verdict];

  return (
    <div style={{
      background: "var(--color-background-primary)",
      border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: 12, overflow: "hidden",
    }}>
      {/* Toolbar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 12, padding: "0.75rem 1rem",
        borderBottom: "0.5px solid var(--color-border-tertiary)",
        background: "var(--color-background-secondary)",
      }}>
        <span style={{ fontSize: 13, fontWeight: 500, flex: 1 }}>GradCAM heatmap</span>

        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <input
            type="checkbox"
            checked={showHeatmap}
            onChange={e => setShowHeatmap(e.target.checked)}
            style={{ accentColor: verdictColor }}
          />
          Heatmap overlay
        </label>

        {showHeatmap && (
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            Opacity
            <input
              type="range" min={20} max={100} value={opacity}
              onChange={e => setOpacity(+e.target.value)}
              style={{ width: 80, accentColor: verdictColor }}
            />
            {opacity}%
          </label>
        )}
      </div>

      {/* Image stack */}
      <div style={{ position: "relative", display: "inline-block", width: "100%" }}>
        {/* Original */}
        <img src={originalUrl} alt="Original" style={{ width: "100%", display: "block", borderRadius: 0 }} />

        {/* Heatmap overlay */}
        {showHeatmap && (
          <img
            src={heatmapUrl}
            alt="Heatmap"
            style={{
              position: "absolute", inset: 0,
              width: "100%", height: "100%",
              objectFit: "cover",
              opacity: opacity / 100,
              mixBlendMode: "multiply",
              transition: "opacity 0.15s",
            }}
          />
        )}

        {/* Region bounding boxes */}
        {regions.map((r, i) => (
          <div key={i} style={{
            position: "absolute",
            left:   `${r.x * 100}%`,
            top:    `${r.y * 100}%`,
            width:  `${r.w * 100}%`,
            height: `${r.h * 100}%`,
            border: `2px solid ${verdictColor}`,
            borderRadius: 4,
            pointerEvents: "none",
          }}>
            <span style={{
              position: "absolute", top: -18, left: 0,
              background: verdictColor, color: "#fff",
              fontSize: 10, padding: "1px 5px", borderRadius: 3,
            }}>
              {r.label ?? "Manipulation"} {(r.score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div style={{ padding: "0.75rem 1rem", fontSize: 11, color: "var(--color-text-secondary)" }}>
        🔴 High manipulation probability &nbsp;·&nbsp; 🟡 Medium &nbsp;·&nbsp; 🟢 Low
        {regions.length > 0 && <span> &nbsp;·&nbsp; {regions.length} region(s) flagged</span>}
      </div>
    </div>
  );
}
