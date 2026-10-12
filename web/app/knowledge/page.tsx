"use client";
import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { UploadCloud, Link2, RefreshCw, Package, CheckCircle2, Loader2 } from "lucide-react";
import PageHead from "../../components/PageHead";
import { api, type InventoryRow } from "../../lib/api";
import { useStore } from "../../lib/store";

type Job = { name: string; state: "working" | "done" | "error"; note?: string };

export default function KnowledgePage() {
  const { health, refreshHealth, toast } = useStore();
  const [rows, setRows] = useState<InventoryRow[]>([]);
  const [url, setUrl] = useState("");
  const [over, setOver] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows(await api.inventory()); } catch {}
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const track = async (name: string, fn: () => Promise<unknown>) => {
    setJobs((j) => [{ name, state: "working" }, ...j]);
    try {
      await fn();
      setJobs((j) => j.map((x) => (x.name === name ? { ...x, state: "done" } : x)));
    } catch (e) {
      setJobs((j) => j.map((x) => (x.name === name ? { ...x, state: "error", note: (e as Error).message } : x)));
    }
    await Promise.all([load(), refreshHealth()]);
  };

  const onFiles = async (files: FileList | null) => {
    if (!files) return;
    for (const f of Array.from(files)) await track(f.name, () => api.upload(f));
  };
  const addUrl = async () => {
    if (!url.trim()) return;
    const u = url.trim(); setUrl("");
    await track(u, () => api.url(u));
  };

  return (
    <>
      <PageHead title={<>Feed the <span className="grad">brain</span></>}
        sub="Drop in real files or point WhyBot at any public docs site. HydraDB extracts entities and relationships automatically." />

      <div className="grid2">
        <motion.label className={`drop glass ${over ? "over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); onFiles(e.dataTransfer.files); }}
          whileHover={{ scale: 1.01 }} animate={over ? { scale: 1.03 } : { scale: 1 }}>
          <input type="file" multiple hidden accept=".pdf,.md,.txt,.csv,.json" onChange={(e) => onFiles(e.target.files)} />
          <motion.div animate={{ y: [0, -6, 0] }} transition={{ duration: 2.4, repeat: Infinity }}>
            <UploadCloud size={40} style={{ color: "var(--accent)" }} />
          </motion.div>
          <h3 style={{ margin: "10px 0 4px", textTransform: "none", letterSpacing: 0, fontSize: 17, color: "var(--text)" }}>Drop files here</h3>
          <div className="muted small">PDF · Markdown · TXT · CSV · JSON — notes, postmortems, Slack or Jira exports</div>
        </motion.label>

        <div className="glass card" style={{ marginBottom: 0 }}>
          <h3><Link2 size={14} style={{ verticalAlign: -2 }} /> Add a web page or docs site</h3>
          <form className="row" onSubmit={(e) => { e.preventDefault(); addUrl(); }}>
            <input className="input" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://docs.hydradb.com/" />
            <button className="btn" type="submit">Add</button>
          </form>
          <div className="row wrap" style={{ marginTop: 10 }}>
            {["https://docs.hydradb.com/", "https://hydradb.com/blog/build-company-brain-ai-agents"].map((u) => (
              <button key={u} className="chip" onClick={() => setUrl(u)}>{u.replace("https://", "")}</button>
            ))}
          </div>
          {!health?.sample_loaded && (
            <button className="btn-ghost" style={{ marginTop: 16 }}
              onClick={() => track("Starter data", async () => { await api.sample(); toast("Starter data loaded"); })}>
              <Package size={16} /> No docs handy? Load starter data
            </button>
          )}
        </div>
      </div>

      <AnimatePresence>
        {jobs.length > 0 && (
          <motion.div className="glass card" style={{ marginTop: 14 }} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
            <h3>Activity</h3>
            {jobs.slice(0, 6).map((j) => (
              <motion.div key={j.name} className="row small" style={{ padding: "6px 0" }} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}>
                {j.state === "working" ? <Loader2 size={16} className="spin-icon" style={{ animation: "spin 1s linear infinite" }} />
                  : j.state === "done" ? <CheckCircle2 size={16} color="var(--good)" /> : <span style={{ color: "var(--bad)" }}>✕</span>}
                <span>{j.name}</span>
                <span className="faint">{j.state === "working" ? "ingesting…" : j.state === "done" ? "added" : j.note}</span>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid4" style={{ marginTop: 14 }}>
        {[
          ["Documents", health?.docs ?? 0], ["Relationships", health?.edges ?? 0],
          ["Questions answered", health?.questions ?? 0], ["Engine", health?.mode === "hydradb" ? "HydraDB" : "Offline"],
        ].map(([k, v], i) => (
          <motion.div key={String(k)} className="glass stat" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
            <b className="grad">{v}</b><span>{k}</span>
          </motion.div>
        ))}
      </div>

      <div className="glass card" style={{ marginTop: 14 }}>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
          <h3 style={{ margin: 0 }}>What's in the brain</h3>
          <button className="btn-ghost small" onClick={load}>
            <motion.span animate={loading ? { rotate: 360 } : {}} transition={{ repeat: loading ? Infinity : 0, duration: 1 }} style={{ display: "inline-flex" }}>
              <RefreshCw size={14} /></motion.span> Refresh status
          </button>
        </div>
        {rows.length ? (
          <table className="table">
            <thead><tr><th>Title</th><th>Type</th><th>Indexing</th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <motion.tr key={r.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}>
                  <td>{r.title}</td><td className="muted">{r.type}</td>
                  <td><span className={`status-pill ${r.status ?? ""}`}>{r.status ?? "local"}</span></td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        ) : <div className="empty">Nothing yet — drop a file or add a URL above.</div>}
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </>
  );
}
