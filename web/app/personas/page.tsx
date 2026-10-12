"use client";
import { useState } from "react";
import { motion } from "motion/react";
import { Plus, Brain, Check } from "lucide-react";
import PageHead from "../../components/PageHead";
import { api } from "../../lib/api";
import { useStore } from "../../lib/store";

export default function PersonasPage() {
  const { personas, persona, setPersona, refreshPersonas, toast, setProfileOpen } = useStore();
  const [label, setLabel] = useState("");
  const [mems, setMems] = useState("");
  const [fact, setFact] = useState("");

  const create = async () => {
    if (!label.trim()) return;
    const r = await api.createPersona(label.trim(), mems.split("\n"));
    await refreshPersonas(); setPersona(r.key); setLabel(""); setMems("");
    toast(`Persona “${label}” created`);
  };
  const remember = async () => {
    if (!fact.trim()) return;
    await api.memory(persona, fact.trim()); await refreshPersonas(); setFact("");
    toast("Saved to memory");
  };

  return (
    <>
      <PageHead title={<>Personas & <span className="grad">memory</span></>}
        sub="Each persona is a HydraDB memory collection merged with company knowledge at query time. Same facts, answer shaped for the person asking.">
        <button className="btn-ghost" style={{ marginTop: 14 }} onClick={() => setProfileOpen(true)}>Use my own profile</button>
      </PageHead>

      <div className="grid3">
        {Object.entries(personas).map(([k, p], i) => {
          const on = k === persona;
          return (
            <motion.div key={k} className={`glass card ${on ? "answer win" : ""}`} style={{ cursor: "pointer", marginBottom: 0 }}
              onClick={() => setPersona(k)} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }} whileHover={{ y: -4 }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <b style={{ fontSize: 16 }}>{p.label}</b>
                {on && <span className="tag" style={{ margin: 0 }}><Check size={12} /> active</span>}
              </div>
              <ul className="small muted" style={{ paddingLeft: 18, marginBottom: 0 }}>
                {p.memories.length ? p.memories.slice(0, 4).map((m) => <li key={m}>{m}</li>) : <li>No memories yet</li>}
              </ul>
            </motion.div>
          );
        })}
      </div>

      <div className="grid2" style={{ marginTop: 14 }}>
        <div className="glass card">
          <h3><Brain size={14} style={{ verticalAlign: -2 }} /> Remember something for “{personas[persona]?.label ?? persona}”</h3>
          <form className="row" onSubmit={(e) => { e.preventDefault(); remember(); }}>
            <input className="input" value={fact} onChange={(e) => setFact(e.target.value)} placeholder="I own the mobile release" />
            <button className="btn" type="submit">Remember</button>
          </form>
          <p className="faint small">Stored in this persona's HydraDB memory collection.</p>
        </div>
        <div className="glass card">
          <h3><Plus size={14} style={{ verticalAlign: -2 }} /> Create a persona</h3>
          <input className="input" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Support Lead, Investor, Student…" />
          <textarea className="textarea" style={{ marginTop: 10 }} rows={3} value={mems} onChange={(e) => setMems(e.target.value)}
            placeholder={"What should the brain know about them? One per line."} />
          <button className="btn" style={{ marginTop: 10 }} onClick={create}>Create persona</button>
        </div>
      </div>
    </>
  );
}
