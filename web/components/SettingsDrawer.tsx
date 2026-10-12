"use client";
import { AnimatePresence, motion } from "motion/react";
import { X, RotateCcw, ExternalLink } from "lucide-react";
import { useState } from "react";
import { useStore } from "../lib/store";
import { api } from "../lib/api";
import Toggle from "./Toggle";

export default function SettingsDrawer() {
  const { settingsOpen, setSettingsOpen, settings, setSettings, personas, health, refreshHealth, refreshPersonas, toast, setPersona } = useStore();
  const [confirm, setConfirm] = useState(false);

  const reset = async () => {
    await api.reset(); await refreshHealth(); await refreshPersonas(); setPersona("engineer");
    setConfirm(false); toast("Brain cleared (HydraDB data untouched)");
  };

  return (
    <AnimatePresence>
      {settingsOpen && (
        <>
          <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setSettingsOpen(false)} />
          <motion.aside className="drawer glass" initial={{ x: 460 }} animate={{ x: 0 }} exit={{ x: 460 }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h2 style={{ margin: 0 }}>Settings</h2>
              <button className="icon-btn" onClick={() => setSettingsOpen(false)} aria-label="Close"><X size={16} /></button>
            </div>

            <h3 className="faint" style={{ fontSize: 12, letterSpacing: ".12em", margin: "22px 0 4px" }}>APPEARANCE</h3>
            <div className="setting">
              <div><b>Reduce motion</b><span>Turn off animations</span></div>
              <Toggle on={settings.reduceMotion} onChange={(v) => setSettings({ reduceMotion: v })} />
            </div>

            <h3 className="faint" style={{ fontSize: 12, letterSpacing: ".12em", margin: "22px 0 4px" }}>ANSWERS</h3>
            <div className="setting">
              <div><b>Compare mode by default</b><span>Plain search next to WhyBot</span></div>
              <Toggle on={settings.compareDefault} onChange={(v) => setSettings({ compareDefault: v })} />
            </div>
            <div className="setting">
              <div><b>Graph context</b><span>Follow relationships between documents</span></div>
              <Toggle on={settings.graphDefault} onChange={(v) => setSettings({ graphDefault: v })} />
            </div>
            <div className="setting">
              <div><b>Default persona</b><span>Used when the app opens</span></div>
              <select className="select" style={{ width: 170 }} value={settings.defaultPersona}
                onChange={(e) => setSettings({ defaultPersona: e.target.value })}>
                {Object.entries(personas).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </div>

            <h3 className="faint" style={{ fontSize: 12, letterSpacing: ".12em", margin: "22px 0 4px" }}>CONNECTION</h3>
            <div className="setting">
              <div><b>Engine</b><span>{health ? (health.mode === "hydradb" ? `HydraDB · database “${health.database}”` : "Offline mode (no HydraDB key)") : "Backend not reachable"}</span></div>
              <span className={`dot ${health?.mode === "hydradb" ? "live" : "off"}`} />
            </div>
            <div className="setting">
              <div><b>API reference</b><span>Interactive backend docs</span></div>
              <a className="btn-ghost" href="/api/docs" target="_blank" rel="noreferrer">Open <ExternalLink size={14} /></a>
            </div>

            <h3 className="faint" style={{ fontSize: 12, letterSpacing: ".12em", margin: "22px 0 4px" }}>DATA</h3>
            <div className="setting">
              <div><b>Clear this brain</b><span>Removes local docs list, graph and custom personas</span></div>
              {confirm
                ? <div className="row"><button className="btn-ghost" onClick={() => setConfirm(false)}>Cancel</button>
                    <button className="btn-ghost btn-danger" onClick={reset}>Confirm</button></div>
                : <button className="btn-ghost btn-danger" onClick={() => setConfirm(true)}><RotateCcw size={14} /> Reset</button>}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
