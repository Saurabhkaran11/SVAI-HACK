"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { Send, Database } from "lucide-react";
import PageHead from "../components/PageHead";
import AnswerCard, { AnswerSkeleton } from "../components/AnswerCard";
import Toggle from "../components/Toggle";
import { api, type Answer } from "../lib/api";
import { useStore } from "../lib/store";

type Result = { single?: Answer; plain?: Answer; smart?: Answer };

export default function AskPage() {
  const { health, persona, setPersona, personas, settings, refreshHealth, profile, setProfileOpen } = useStore();
  const [q, setQ] = useState("");
  const [compare, setCompare] = useState(true);
  const [graph, setGraph] = useState(true);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => { setCompare(settings.compareDefault); setGraph(settings.graphDefault); }, [settings.compareDefault, settings.graphDefault]);

  const suggestions = health ? (health.sample_loaded ? health.sample_questions : health.starter_questions) : [];

  const ask = async (question = q) => {
    if (!question.trim()) return;
    setQ(question); setBusy(true); setErr(""); setRes(null);
    try {
      if (compare) {
        const r = await api.compare(question, persona);
        setRes({ plain: r.without_graph, smart: r.with_graph });
      } else {
        setRes({ single: await api.ask(question, persona, graph) });
      }
      refreshHealth();
    } catch (e) { setErr((e as Error).message); refreshHealth(); }
    setBusy(false);
  };

  return (
    <>
      <PageHead title={<>Ask across <span className="grad">everything</span> your team knows.</>}
        sub="WhyBot links docs, chats and tickets into a knowledge graph. Answers come with who owns it, what depends on it, and sources — tailored to who's asking." />
      {health?.public && (
        <div className="demo-note" role="note">
          <b>Public demo:</b> everyone shares one brain. Add your own public docs on the Knowledge page, then ask about them here.
        </div>
      )}

      {health && health.docs === 0 && (
        <motion.div className="glass card row wrap" initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ justifyContent: "space-between" }}>
          <span className="muted"><Database size={16} style={{ verticalAlign: -3 }} /> Your brain is empty. Add files or a docs URL to get started.</span>
          <Link href="/knowledge" className="btn">Feed the brain</Link>
        </motion.div>
      )}

      <div className="glass card">
        <form className="row" onSubmit={(e) => { e.preventDefault(); ask(); }}>
          <input className="input" style={{ fontSize: 16, padding: "15px 18px" }} value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="What would break if we changed X? Who owns Y? Why did we decide Z?" />
          <motion.button className="btn" type="submit" disabled={busy} whileTap={{ scale: 0.95 }}>
            <Send size={16} /> {busy ? "Thinking…" : "Ask"}
          </motion.button>
        </form>
        <div className="row wrap" style={{ marginTop: 12 }}>
          {suggestions.map((s, i) => (
            <motion.button key={s} className="chip" onClick={() => ask(s)} initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 * i }} whileHover={{ y: -2 }}>{s}</motion.button>
          ))}
        </div>
        <div className="row wrap" style={{ marginTop: 16, gap: 22 }}>
          <label className="row small muted">Asking as
            <select className="select" style={{ width: 190, padding: "8px 12px" }} value={persona} onChange={(e) => setPersona(e.target.value)}>
              {Object.entries(personas).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </label>
          {!profile.name && <button className="btn-ghost small" onClick={() => setProfileOpen(true)}>Set up my profile</button>}
          <span className="row small muted"><Toggle on={compare} onChange={setCompare} label="Compare" /> Compare plain vs WhyBot</span>
          <span className="row small muted" style={{ opacity: compare ? 0.45 : 1 }}>
            <Toggle on={graph} onChange={(v) => !compare && setGraph(v)} label="Graph" /> Graph context
          </span>
        </div>
      </div>

      {err && <div className="glass card" style={{ color: "var(--text)", borderColor: "#d1d5db" }}>Something went wrong: {err}</div>}

      {busy && (compare
        ? <div className="grid2"><AnswerSkeleton title="Plain search" /><AnswerSkeleton title="WhyBot" /></div>
        : <AnswerSkeleton title="Answer" />)}

      {res?.plain && res.smart && (
        <div className="grid2">
          <AnswerCard a={res.plain} title="Plain search" />
          <AnswerCard a={res.smart} title="WhyBot" win delay={0.15} />
        </div>
      )}
      {res?.single && <AnswerCard a={res.single} title="Answer" win={graph} />}
    </>
  );
}
