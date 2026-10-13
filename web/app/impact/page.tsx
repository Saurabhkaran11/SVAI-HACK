"use client";
import { useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { motion, animate, useMotionValue, useTransform } from "motion/react";
import { useEffect } from "react";
import { Radar, Users, AlertTriangle, Send, Copy, Zap, Layers } from "lucide-react";
import PageHead from "../../components/PageHead";
import BlastRings from "../../components/BlastRings";
import GraphView from "../../components/GraphView";
import { api, type Impact } from "../../lib/api";
import { useStore } from "../../lib/store";

const EXAMPLES = [
  "Deprecate payments-api-v1 next month",
  "Turn off the billing-service feature flag use_payments_v2",
  "Migrate auth-service to a new rate-limit-config",
];

function Score({ value, level }: { value: number; level: string }) {
  const mv = useMotionValue(0);
  const rounded = useTransform(mv, (v) => Math.round(v));
  const [n, setN] = useState(0);
  useEffect(() => { const c = animate(mv, value, { duration: 1.2, ease: "easeOut" }); const u = rounded.on("change", setN); return () => { c.stop(); u(); }; }, [value, mv, rounded]);
  const color = "var(--accent)";
  return (
    <div className="glass stat" style={{ textAlign: "center" }}>
      <svg viewBox="0 0 120 120" width="120" height="120">
        <circle cx="60" cy="60" r="50" fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <motion.circle cx="60" cy="60" r="50" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          transform="rotate(-90 60 60)" initial={{ pathLength: 0 }} animate={{ pathLength: value / 100 }} transition={{ duration: 1.2 }} />
        <text x="60" y="66" textAnchor="middle" fill="#111827" fontSize="28" fontWeight="800">{n}</text>
      </svg>
      <b style={{ fontSize: 16, color: "var(--text)" }}>{level} risk</b>
    </div>
  );
}

export default function ImpactPage() {
  const { persona, health, toast, refreshHealth } = useStore();
  const [change, setChange] = useState("");
  const [busy, setBusy] = useState(false);
  const [r, setR] = useState<Impact | null>(null);
  const [err, setErr] = useState("");

  const run = async (c = change) => {
    if (!c.trim()) return;
    setChange(c); setBusy(true); setErr(""); setR(null);
    try { setR(await api.impact(c, persona)); refreshHealth(); } catch (e) { setErr((e as Error).message); refreshHealth(); }
    setBusy(false);
  };
  useEffect(() => {  // deep link from the graph explorer: /impact?change=...
    const c = new URLSearchParams(window.location.search).get("change");
    if (c) run(c);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const copy = (t: string) => { navigator.clipboard?.writeText(t); toast("Message copied"); };
  const ripple = r ? r.affected.filter((a) => a.hop > 0) : [];

  return (
    <>
      <PageHead title={<>Know the <span className="grad">blast radius</span> before you ship.</>}
        sub="Describe a change. WhyBot walks your company's knowledge graph to find what breaks, who to tell, and what went wrong last time." />

      {health && health.docs === 0 && (
        <div className="glass card row wrap" style={{ justifyContent: "space-between" }}>
          <span className="muted">Add your docs first so WhyBot has a graph to walk.</span>
          <Link href="/knowledge" className="btn">Feed the brain</Link>
        </div>
      )}

      <div className="glass card">
        <form className="row" onSubmit={(e) => { e.preventDefault(); run(); }}>
          <Radar size={20} style={{ color: "var(--accent)", flexShrink: 0 }} />
          <input className="input" style={{ fontSize: 16, padding: "15px 18px" }} value={change} onChange={(e) => setChange(e.target.value)}
            placeholder="We're planning to… (deprecate an API, reorg a team, change a config)" />
          <motion.button className="btn" type="submit" disabled={busy} whileTap={{ scale: 0.95 }}>
            {busy ? "Scanning…" : "Check impact"}
          </motion.button>
        </form>
        <div className="row wrap" style={{ marginTop: 12 }}>
          {EXAMPLES.map((e, i) => (
            <motion.button key={e} className="chip" onClick={() => run(e)} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }} whileHover={{ y: -2 }}>{e}</motion.button>
          ))}
        </div>
      </div>

      {busy && (
        <div className="glass card" style={{ display: "grid", placeItems: "center", padding: 50 }}>
          <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}><Radar size={46} style={{ color: "var(--accent)" }} /></motion.div>
          <div className="muted" style={{ marginTop: 10 }}>Walking the dependency graph…</div>
        </div>
      )}
      {err && <div className="glass card" style={{ color: "var(--text)", borderColor: "#d1d5db" }}>Something went wrong: {err}</div>}

      {r && (
        <>
          <div className="grid4">
            <Score value={r.risk.score} level={r.risk.level} />
            {[
              [Layers, ripple.length, "Systems affected"], [Users, Object.keys(r.owners).length, "Teams to notify"],
              [AlertTriangle, r.incidents.length, "Related incidents"],
            ].map(([Icon, v, k], i) => {
              const I = Icon as typeof Layers;
              return (
                <motion.div key={String(k)} className="glass stat" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.08 }}>
                  <I size={20} style={{ color: "var(--accent)" }} /><b className="grad">{String(v)}</b><span>{String(k)}</span>
                </motion.div>
              );
            })}
          </div>

          <div className="grid2" style={{ marginTop: 14 }}>
            <motion.div className="glass card" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h3>Shockwave</h3>
              {ripple.length ? <BlastRings impact={r} />
                : <div className="empty">Nothing in the graph matched this change yet. Try naming a system, team or person from your docs.</div>}
            </motion.div>
            <motion.div className="glass card answer win" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
              <h3>Impact brief</h3>
              <div className="md"><ReactMarkdown>{r.brief}</ReactMarkdown></div>
            </motion.div>
          </div>

          <div className="grid2">
            <div className="glass card">
              <h3><Layers size={14} style={{ verticalAlign: -2 }} /> What breaks, hop by hop</h3>
              {r.affected.map((a, i) => (
                <motion.div key={a.name} className="row small" style={{ padding: "7px 0", borderBottom: "1px solid var(--stroke-soft)" }}
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}>
                  <span className="tag" style={{ margin: 0, minWidth: 54, justifyContent: "center" }}>{a.hop === 0 ? "change" : `hop ${a.hop}`}</span>
                  <b>{a.name}</b><span className="faint">{a.hop ? `→ ${a.via}` : ""}</span>
                </motion.div>
              ))}
              {r.incidents.length > 0 && (<>
                <h3 style={{ marginTop: 16 }}><AlertTriangle size={14} style={{ verticalAlign: -2 }} /> Last time this went wrong</h3>
                {r.incidents.map((t) => <div key={t} className="path">{t}</div>)}
              </>)}
              {r.people.length > 0 && (<>
                <h3 style={{ marginTop: 16 }}>People mentioned</h3>
                <div className="row wrap">{r.people.map((p) => <span key={p} className="chip">{p}</span>)}</div>
              </>)}
            </div>
            <div className="glass card">
              <h3><Send size={14} style={{ verticalAlign: -2 }} /> Heads-up drafts</h3>
              {r.notify.length ? r.notify.map((n, i) => (
                <motion.div key={n.to} className="glass-soft" style={{ padding: 12, marginBottom: 10 }} initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + i * 0.08 }}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <b>To: {n.to}</b>
                    <button className="btn-ghost small" onClick={() => copy(n.message)}><Copy size={13} /> Copy</button>
                  </div>
                  <p className="muted small" style={{ margin: "6px 0 0" }}>{n.message}</p>
                </motion.div>
              )) : <div className="faint small">No owning teams found for the affected systems.</div>}
            </div>
          </div>

          {r.paths.length > 0 && (
            <div className="glass card">
              <h3>Evidence graph</h3>
              <GraphView paths={r.paths} height={420} />
              <details className="fold"><summary><Zap size={13} style={{ verticalAlign: -2 }} /> Under the hood (HydraDB)</summary>
                <div style={{ marginTop: 8 }}>{r.features.map((f) => <span key={f} className="tag">{f}</span>)}</div>
                <div className="faint small" style={{ marginTop: 8 }}>engine: {r.mode} · {r.latency_ms} ms</div>
              </details>
            </div>
          )}
        </>
      )}
    </>
  );
}
