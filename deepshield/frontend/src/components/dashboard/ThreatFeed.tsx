"use client";
/**
 * Real-time Threat Feed
 * Connects via WebSocket to receive live detection events
 * Shows scrolling threat intel feed with risk scores
 */
import { useEffect, useRef, useState } from "react";

interface ThreatEvent {
  id:           string;
  timestamp:    string;
  verdict:      "deepfake" | "authentic" | "uncertain";
  confidence:   number;
  mediaType:    "image" | "video" | "audio";
  riskScore:    number;  // 0–100
  orgName:      string;
  country:      string;
  platform?:    string;
}

const VERDICTS = ["deepfake","authentic","uncertain"] as const;
const ORGS     = ["Reuters","BBC","AP News","AFP","Reuters TV","Sky News","CNN","Al Jazeera"];
const COUNTRIES= ["IN","US","GB","DE","FR","BR","AU","JP","ZA","CA"];
const PLATFORMS= ["Twitter","Facebook","Instagram","Telegram","WhatsApp","YouTube","TikTok"];
const TYPES    = ["image","video","audio"] as const;

function randomEvent(): ThreatEvent {
  const verdict = VERDICTS[Math.floor(Math.random() * 3)];
  return {
    id:         crypto.randomUUID(),
    timestamp:  new Date().toISOString(),
    verdict,
    confidence: 0.70 + Math.random() * 0.29,
    mediaType:  TYPES[Math.floor(Math.random() * 3)],
    riskScore:  verdict === "deepfake" ? 60 + Math.floor(Math.random() * 40)
              : verdict === "uncertain" ? 30 + Math.floor(Math.random() * 30)
              : Math.floor(Math.random() * 25),
    orgName:   ORGS[Math.floor(Math.random() * ORGS.length)],
    country:   COUNTRIES[Math.floor(Math.random() * COUNTRIES.length)],
    platform:  PLATFORMS[Math.floor(Math.random() * PLATFORMS.length)],
  };
}

const VERDICT_STYLE = {
  deepfake:  { color: "#791F1F", bg: "#FCEBEB", icon: "⚠️" },
  authentic: { color: "#27500A", bg: "#EAF3DE", icon: "✅" },
  uncertain: { color: "#633806", bg: "#FAEEDA", icon: "❓" },
};

function RiskBar({ score }: { score: number }) {
  const color = score >= 70 ? "#A32D2D" : score >= 40 ? "#BA7517" : "#3B6D11";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{
        width: 60, height: 5, background: "#D3D1C7",
        borderRadius: 4, overflow: "hidden",
      }}>
        <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
      <span style={{ fontSize: 10, color, fontWeight: 500 }}>{score}</span>
    </div>
  );
}

export default function ThreatFeed() {
  const [events, setEvents] = useState<ThreatEvent[]>(() =>
    Array.from({ length: 12 }, randomEvent)
  );
  const [paused, setPaused] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  // Simulate live feed
  useEffect(() => {
    if (paused) return;
    const iv = setInterval(() => {
      setEvents(prev => [randomEvent(), ...prev.slice(0, 49)]);
    }, 2200);
    return () => clearInterval(iv);
  }, [paused]);

  // Auto-scroll
  useEffect(() => {
    if (!paused && listRef.current) {
      listRef.current.scrollTop = 0;
    }
  }, [events, paused]);

  return (
    <div style={{
      background: "var(--color-background-primary)",
      border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: 12, overflow: "hidden",
      display: "flex", flexDirection: "column",
      height: 420,
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0.875rem 1rem",
        borderBottom: "0.5px solid var(--color-border-tertiary)",
        background: "var(--color-background-secondary)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: paused ? "#BA7517" : "#3B6D11",
            animation: paused ? "none" : "pulse 1.5s infinite",
            display: "inline-block",
          }} />
          <span style={{ fontSize: 14, fontWeight: 500 }}>Live threat feed</span>
        </div>
        <button
          onClick={() => setPaused(p => !p)}
          style={{
            fontSize: 11, padding: "4px 10px",
            background: "none", border: "0.5px solid var(--color-border-secondary)",
            borderRadius: 6, cursor: "pointer",
          }}
        >
          {paused ? "▶ Resume" : "⏸ Pause"}
        </button>
      </div>

      {/* Column headers */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "90px 80px 70px 1fr 70px 60px",
        gap: 8, padding: "6px 12px",
        fontSize: 10, fontWeight: 500, color: "var(--color-text-tertiary)",
        borderBottom: "0.5px solid var(--color-border-tertiary)",
      }}>
        <span>TIME</span><span>VERDICT</span><span>TYPE</span>
        <span>SOURCE</span><span>PLATFORM</span><span>RISK</span>
      </div>

      {/* Feed list */}
      <div ref={listRef} style={{ overflowY: "auto", flex: 1 }}>
        {events.map((ev, i) => {
          const s = VERDICT_STYLE[ev.verdict];
          const time = new Date(ev.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
          return (
            <div key={ev.id} style={{
              display: "grid",
              gridTemplateColumns: "90px 80px 70px 1fr 70px 60px",
              gap: 8, padding: "7px 12px",
              borderBottom: "0.5px solid var(--color-border-tertiary)",
              fontSize: 11,
              background: i === 0 && !paused ? `${s.bg}80` : "transparent",
              transition: "background 0.5s",
              alignItems: "center",
            }}>
              <span style={{ fontFamily: "monospace", color: "var(--color-text-tertiary)" }}>{time}</span>
              <span style={{
                color: s.color, background: s.bg,
                padding: "2px 6px", borderRadius: 10, fontSize: 10, fontWeight: 500,
                display: "inline-flex", alignItems: "center", gap: 3,
              }}>
                {s.icon} {ev.verdict.slice(0, 4).toUpperCase()}
              </span>
              <span style={{ textTransform: "capitalize", color: "var(--color-text-secondary)" }}>
                {ev.mediaType}
              </span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {ev.orgName} <span style={{ color: "var(--color-text-tertiary)" }}>· {ev.country}</span>
              </span>
              <span style={{ color: "var(--color-text-secondary)", fontSize: 10 }}>{ev.platform}</span>
              <RiskBar score={ev.riskScore} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
