"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { Search, RefreshCw } from "lucide-react";
import PageHead from "../../components/PageHead";
import GraphView from "../../components/GraphView";
import { api, parsePath } from "../../lib/api";

export default function GraphPage() {
  const [edges, setEdges] = useState<string[]>([]);
  const [focus, setFocus] = useState("");
  const [loaded, setLoaded] = useState(false);

  const load = async () => { try { setEdges((await api.graph()).edges); } catch {} setLoaded(true); };
  useEffect(() => { load(); }, []);

  const top = useMemo(() => {
    const deg = new Map<string, number>();
    edges.forEach((e) => { const t = parsePath(e); if (t) [t[0], t[2]].forEach((n) => deg.set(n, (deg.get(n) ?? 0) + 1)); });
    return [...deg.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  }, [edges]);

  return (
    <>
      <PageHead title={<>Graph <span className="grad">explorer</span></>}
        sub="Every relationship WhyBot has discovered across your knowledge. Drag nodes, zoom, or search to focus on one person, service or decision." />

      <div className="glass card">
        <div className="row wrap">
          <div className="row" style={{ flex: 1, minWidth: 240 }}>
            <Search size={16} className="muted" />
            <input className="input" value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="Focus on… (e.g. billing, Sarah, payments)" />
          </div>
          <button className="btn-ghost" onClick={load}><RefreshCw size={14} /> Refresh</button>
        </div>
        <div className="row wrap" style={{ marginTop: 10 }}>
          <span className="faint small">Most connected:</span>
          {top.map(([n, d], i) => (
            <motion.button key={n} className="chip" onClick={() => setFocus(n)} initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.04 }}>{n} · {d}</motion.button>
          ))}
          {focus && <button className="chip" onClick={() => setFocus("")}>Clear focus ✕</button>}
        </div>
        {edges.length ? <GraphView paths={edges} height={560} focus={focus} />
          : loaded && <div className="empty">No relationships yet. <Link href="/" className="grad"><b>Ask a question</b></Link> with graph context on, or load starter data on the Knowledge page.</div>}
      </div>

      {edges.length > 0 && (
        <div className="glass card">
          <h3>{edges.length} relationships</h3>
          <div>{edges.filter((e) => !focus || e.toLowerCase().includes(focus.toLowerCase())).slice(0, 60)
            .map((e) => <span key={e} className="path">{e}</span>)}</div>
        </div>
      )}
    </>
  );
}
