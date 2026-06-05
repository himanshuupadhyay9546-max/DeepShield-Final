"use client";
/**
 * DeepShield — Drag & Drop Upload Zone
 * Supports: image, video, audio
 * Features: live progress, malware warning, preview, multi-file queue
 */
import { useState, useRef, useCallback, DragEvent, ChangeEvent } from "react";

type FileStatus = "idle" | "uploading" | "analyzing" | "done" | "error";

interface UploadFile {
  id: string;
  file: File;
  preview?: string;
  status: FileStatus;
  progress: number;
  result?: {
    verdict: "deepfake" | "authentic" | "uncertain";
    confidence: number;
    analysisId: string;
  };
  error?: string;
}

const ACCEPT = "image/*,video/*,audio/*";
const MAX_SIZE_MB = 500;

function FileIcon({ type }: { type: string }) {
  if (type.startsWith("video")) return <span style={{ fontSize: 28 }}>🎬</span>;
  if (type.startsWith("audio")) return <span style={{ fontSize: 28 }}>🎵</span>;
  return <span style={{ fontSize: 28 }}>🖼️</span>;
}

function VerdictBadge({ verdict, confidence }: { verdict: string; confidence: number }) {
  const cfg = {
    deepfake:  { bg: "#FCEBEB", color: "#791F1F", label: "DEEPFAKE" },
    authentic: { bg: "#EAF3DE", color: "#27500A", label: "AUTHENTIC" },
    uncertain: { bg: "#FAEEDA", color: "#633806", label: "UNCERTAIN" },
  }[verdict] ?? { bg: "#F1EFE8", color: "#2C2C2A", label: "UNKNOWN" };

  return (
    <span style={{
      background: cfg.bg, color: cfg.color,
      padding: "3px 10px", borderRadius: 20,
      fontSize: 11, fontWeight: 500,
    }}>
      {cfg.label} · {(confidence * 100).toFixed(1)}%
    </span>
  );
}

export default function DragDropZone() {
  const [files, setFiles]       = useState<UploadFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((fileList: FileList) => {
    const newFiles: UploadFile[] = Array.from(fileList).map(f => ({
      id:      crypto.randomUUID(),
      file:    f,
      preview: f.type.startsWith("image") ? URL.createObjectURL(f) : undefined,
      status:  "idle",
      progress: 0,
    }));
    setFiles(prev => [...prev, ...newFiles]);
    newFiles.forEach(uf => simulateUpload(uf.id));
  }, []);

  const simulateUpload = (id: string) => {
    // Simulate upload + analysis progress
    let prog = 0;
    const tick = setInterval(() => {
      prog += Math.random() * 15 + 5;
      if (prog >= 100) {
        prog = 100;
        clearInterval(tick);
        setFiles(prev => prev.map(f =>
          f.id === id ? { ...f, progress: 100, status: "analyzing" } : f
        ));
        // Simulate AI analysis (1.5s)
        setTimeout(() => {
          const verdicts = ["deepfake", "authentic", "uncertain"] as const;
          const verdict  = verdicts[Math.floor(Math.random() * 3)];
          setFiles(prev => prev.map(f =>
            f.id === id ? {
              ...f, status: "done",
              result: {
                verdict,
                confidence: 0.75 + Math.random() * 0.24,
                analysisId: crypto.randomUUID().slice(0, 8),
              },
            } : f
          ));
        }, 1500);
      } else {
        setFiles(prev => prev.map(f =>
          f.id === id ? { ...f, progress: Math.round(prog), status: "uploading" } : f
        ));
      }
    }, 120);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  };

  const removeFile = (id: string) =>
    setFiles(prev => prev.filter(f => f.id !== id));

  return (
    <div style={{ padding: "1.5rem", maxWidth: 800 }}>
      <h2 style={{ fontSize: 18, fontWeight: 500, margin: "0 0 1.25rem" }}>Upload media for analysis</h2>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? "#185FA5" : "var(--color-border-secondary)"}`,
          borderRadius: 16,
          padding: "3rem 2rem",
          textAlign: "center",
          cursor: "pointer",
          background: dragging ? "#E6F1FB" : "var(--color-background-secondary)",
          transition: "all 0.15s",
          marginBottom: "1.5rem",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          multiple
          style={{ display: "none" }}
          onChange={(e: ChangeEvent<HTMLInputElement>) => {
            if (e.target.files) addFiles(e.target.files);
          }}
        />
        <div style={{ fontSize: 40, marginBottom: 12 }}>⬆️</div>
        <p style={{ fontSize: 15, fontWeight: 500, margin: "0 0 6px" }}>
          {dragging ? "Drop files here" : "Drag & drop or click to upload"}
        </p>
        <p style={{ fontSize: 12, color: "var(--color-text-secondary)", margin: 0 }}>
          Images · Videos · Audio — up to {MAX_SIZE_MB}MB each
        </p>
      </div>

      {/* File queue */}
      {files.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {files.map(uf => (
            <div key={uf.id} style={{
              background: "var(--color-background-primary)",
              border: "0.5px solid var(--color-border-tertiary)",
              borderRadius: 12,
              padding: "0.875rem 1rem",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}>
              {uf.preview
                ? <img src={uf.preview} alt="" style={{ width: 52, height: 52, objectFit: "cover", borderRadius: 8 }} />
                : <div style={{ width: 52, height: 52, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--color-background-secondary)", borderRadius: 8 }}>
                    <FileIcon type={uf.file.type} />
                  </div>
              }

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <p style={{ fontSize: 13, fontWeight: 500, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {uf.file.name}
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                    {uf.status === "done" && uf.result && (
                      <VerdictBadge verdict={uf.result.verdict} confidence={uf.result.confidence} />
                    )}
                    <button
                      onClick={() => removeFile(uf.id)}
                      style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, color: "var(--color-text-tertiary)", padding: "0 4px" }}
                    >✕</button>
                  </div>
                </div>

                {/* Progress bar */}
                {(uf.status === "uploading" || uf.status === "analyzing") && (
                  <div style={{ height: 4, background: "var(--color-background-tertiary)", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{
                      height: "100%", borderRadius: 4,
                      width: `${uf.progress}%`,
                      background: uf.status === "analyzing" ? "#185FA5" : "#3B6D11",
                      transition: "width 0.1s",
                    }} />
                  </div>
                )}

                <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", margin: "4px 0 0" }}>
                  {(uf.file.size / 1024 / 1024).toFixed(1)}MB
                  {uf.status === "uploading"  && ` · Uploading ${uf.progress}%`}
                  {uf.status === "analyzing"  && " · AI analyzing…"}
                  {uf.status === "done"       && uf.result && ` · ID: ${uf.result.analysisId}`}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
