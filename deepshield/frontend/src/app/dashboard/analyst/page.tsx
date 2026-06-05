"use client";
/**
 * Analyst Dashboard — full investigation workspace
 * Upload + Results + Heatmap + Threat Feed + Model Breakdown
 */
import { useState } from "react";
import DragDropZone      from "@/components/upload/DragDropZone";
import ConfidenceGauge   from "@/components/results/ConfidenceGauge";
import HeatmapOverlay    from "@/components/results/HeatmapOverlay";
import ThreatFeed        from "@/components/dashboard/ThreatFeed";

// Mock result for demo
const DEMO_RESULT = {
  verdict:         "deepfake" as const,
  confidence:      0.962,
  fakeProbability: 0.941,
  processingMs:    187,
  analysisId:      "ds-9f2c1a",
  modelResults: [
    { name: "EfficientNet-B4",   score: 0.951, confidence: 0.971 },
    { name: "XceptionNet",       score: 0.928, confidence: 0.945 },
    { name: "ViT-Base/16",       score: 0.937, confidence: 0.961 },
    { name: "CNN+Transformer",   score: 0.919, confidence: 0.938 },
    { name: "Frequency Domain",  score: 0.884, confidence: 0.902 },
  ],
};

const SCORE_COLOR = (s: number) =>
  s >= 0.8 ? "#A32D2D" : s >= 0.5 ? "#BA7517" : "#3B6D11";

export default function AnalystDashboard() {
  const [tab, setTab] = useState<"upload" | "results" | "feed">("upload");

  const tabs = [
    { id: "upload",  label: "📤 Upload" },
    { id: "results", label: "🔍 Results" },
    { id: "feed",    label: "📡 Live Feed" },
  ] as const;

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ marginBottom: "1.25rem" }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, margin: "0 0 4px" }}>Analyst workspace</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
          Upload · Analyze · Generate forensic evidence
        </p>
      </div>

      {/* Tab bar */}
      <div style={{
        display: "flex", gap: 4, marginBottom: "1.5rem",
        borderBottom: "0.5px solid var(--color-border-tertiary)",
        paddingBottom: 0,
      }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding: "7px 16px", fontSize: 13, cursor: "pointer",
            background: "none", border: "none",
            borderBottom: tab === t.id ? "2px solid #185FA5" : "2px solid transparent",
            color: tab === t.id ? "#185FA5" : "var(--color-text-secondary)",
            fontWeight: tab === t.id ? 500 : 400,
            transition: "all 0.15s",
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "upload" && <DragDropZone />}

      {tab === "results" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 20 }}>
          {/* Left: heatmap + model table */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Mock image + heatmap */}
            <HeatmapOverlay
              originalUrl="https://placehold.co/800x450/1a1a2e/ffffff?text=Sample+Media"
              heatmapUrl="https://placehold.co/800x450/ff4444/ffffff?text=GradCAM+Heatmap"
              regions={[
                { x: 0.12, y: 0.08, w: 0.35, h: 0.55, score: 0.94, label: "Face swap" },
                { x: 0.55, y: 0.62, w: 0.20, h: 0.25, score: 0.71, label: "Artifact" },
              ]}
              verdict="deepfake"
            />

            {/* Per-model breakdown */}
            <div style={{
              background: "var(--color-background-primary)",
              border: "0.5px solid var(--color-border-tertiary)",
              borderRadius: 12, overflow: "hidden",
            }}>
              <div style={{ padding: "0.875rem 1rem", borderBottom: "0.5px solid var(--color-border-tertiary)", background: "var(--color-background-secondary)" }}>
                <span style={{ fontSize: 14, fontWeight: 500 }}>Model breakdown</span>
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "0.5px solid var(--color-border-secondary)" }}>
                    {["Model","Fake score","Confidence","Vote"].map(h => (
                      <th key={h} style={{ padding: "6px 12px", textAlign: "left", fontWeight: 500, fontSize: 11, color: "var(--color-text-secondary)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {DEMO_RESULT.modelResults.map((m, i) => (
                    <tr key={m.name} style={{
                      borderBottom: "0.5px solid var(--color-border-tertiary)",
                      background: i % 2 === 1 ? "var(--color-background-secondary)" : "transparent",
                    }}>
                      <td style={{ padding: "8px 12px", fontWeight: 500 }}>{m.name}</td>
                      <td style={{ padding: "8px 12px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <div style={{ width: 50, height: 4, background: "#D3D1C7", borderRadius: 4, overflow: "hidden" }}>
                            <div style={{ width: `${m.score * 100}%`, height: "100%", background: SCORE_COLOR(m.score), borderRadius: 4 }} />
                          </div>
                          <span style={{ color: SCORE_COLOR(m.score), fontWeight: 500 }}>{(m.score * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                      <td style={{ padding: "8px 12px", color: "var(--color-text-secondary)" }}>{(m.confidence * 100).toFixed(1)}%</td>
                      <td style={{ padding: "8px 12px" }}>
                        <span style={{
                          background: m.score >= 0.5 ? "#FCEBEB" : "#EAF3DE",
                          color: m.score >= 0.5 ? "#791F1F" : "#27500A",
                          padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 500,
                        }}>
                          {m.score >= 0.5 ? "FAKE" : "REAL"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Download report button */}
              <div style={{ padding: "0.875rem 1rem", borderTop: "0.5px solid var(--color-border-tertiary)", display: "flex", gap: 8 }}>
                <button style={{
                  background: "#185FA5", color: "#fff",
                  border: "none", borderRadius: 8, padding: "8px 16px",
                  fontSize: 12, fontWeight: 500, cursor: "pointer",
                }}>
                  📄 Download forensic PDF
                </button>
                <button style={{
                  background: "none", border: "0.5px solid var(--color-border-secondary)",
                  borderRadius: 8, padding: "8px 16px",
                  fontSize: 12, cursor: "pointer",
                }}>
                  ⛓️ Anchor to blockchain
                </button>
              </div>
            </div>
          </div>

          {/* Right: confidence gauge */}
          <div>
            <ConfidenceGauge
              verdict={DEMO_RESULT.verdict}
              fakeProbability={DEMO_RESULT.fakeProbability}
              confidence={DEMO_RESULT.confidence}
              processingMs={DEMO_RESULT.processingMs}
            />

            {/* Analysis metadata */}
            <div style={{
              marginTop: 12,
              background: "var(--color-background-secondary)",
              border: "0.5px solid var(--color-border-tertiary)",
              borderRadius: 10, padding: "0.875rem",
              fontSize: 11,
            }}>
              <p style={{ fontWeight: 500, margin: "0 0 8px", fontSize: 12 }}>Analysis details</p>
              {[
                ["ID",      DEMO_RESULT.analysisId],
                ["Models",  "5 (ensemble)"],
                ["XAI",     "GradCAM ✓"],
                ["Chain",   "Polygon ✓"],
              ].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ color: "var(--color-text-secondary)" }}>{k}</span>
                  <span style={{ fontWeight: 500 }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "feed" && (
        <div>
          <ThreatFeed />
        </div>
      )}
    </div>
  );
}
