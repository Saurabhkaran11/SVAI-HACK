"use client";
import { motion } from "motion/react";
import ReactMarkdown from "react-markdown";
import { Zap, FileText, UserRound } from "lucide-react";
import type { Answer } from "../lib/api";
import GraphView from "./GraphView";

export function AnswerSkeleton({ title }: { title: string }) {
  return (
    <div className="glass answer">
      <h2>{title}</h2>
      {[90, 75, 82, 60].map((w, i) => <div key={i} className="shimmer" style={{ width: `${w}%` }} />)}
    </div>
  );
}

export default function AnswerCard({ a, title, win = false, delay = 0 }: { a: Answer; title: string; win?: boolean; delay?: number }) {
  return (
    <motion.div className={`glass answer ${win ? "win" : ""}`} initial={{ opacity: 0, y: 24, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ delay, type: "spring", stiffness: 140, damping: 18 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>{title}</h2>
        {win && <span className="tag" style={{ margin: 0 }}><Zap size={12} /> graph + memory</span>}
      </div>
      <div className="row wrap faint small" style={{ margin: "6px 0 10px", gap: 14 }}>
        <span>{a.latency_ms} ms</span><span>{a.chunks.length} sources</span>
        <motion.span initial={{ scale: 1.4, color: "#111827" }} animate={{ scale: 1, color: "var(--faint)" }} transition={{ delay: delay + 0.3 }}>
          {a.paths.length} relationships
        </motion.span>
      </div>
      <div className="md"><ReactMarkdown>{a.answer}</ReactMarkdown></div>

      {a.paths.length > 0 && <GraphView paths={a.paths} />}

      <details className="fold">
        <summary><Zap size={13} style={{ verticalAlign: -2 }} /> Under the hood (HydraDB)</summary>
        <div style={{ marginTop: 8 }}>{a.features.map((f) => <span key={f} className="tag">{f}</span>)}</div>
        <div style={{ marginTop: 8 }}>{a.paths.slice(0, 15).map((p) => <span key={p} className="path">{p}</span>)}</div>
        <div className="faint small" style={{ marginTop: 8 }}>engine: {a.mode}</div>
      </details>
      <details className="fold">
        <summary><FileText size={13} style={{ verticalAlign: -2 }} /> Sources ({a.chunks.length})</summary>
        {a.chunks.length ? a.chunks.map((c, i) => (
          <div key={i} className="src"><b>{c.title}</b> <span className="faint">· score {c.score ?? "n/a"}</span>
            <pre>{c.content.slice(0, 400)}</pre></div>
        )) : <div className="faint small" style={{ marginTop: 8 }}>No sources.</div>}
      </details>
      {a.memories.length > 0 && (
        <details className="fold">
          <summary><UserRound size={13} style={{ verticalAlign: -2 }} /> Memory used for this persona</summary>
          <ul className="small muted">{a.memories.map((m) => <li key={m}>{m}</li>)}</ul>
        </details>
      )}
    </motion.div>
  );
}
