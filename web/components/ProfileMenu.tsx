"use client";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { UserRound, Settings, Pencil, Check, X } from "lucide-react";
import { useStore, type Profile } from "../lib/store";

const COLORS = ["#7c8cff", "#c084fc", "#2dd4bf", "#fb7185", "#fbbf24", "#60a5fa"];
const initials = (n: string) => n.trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "?";

export default function ProfileMenu() {
  const { profile, saveProfile, persona, personas, setPersona, setSettingsOpen, toast, profileOpen, setProfileOpen } = useStore();
  const [menu, setMenu] = useState(false);
  const [draft, setDraft] = useState<Profile>(profile);
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => setDraft(profile), [profile, profileOpen]);
  useEffect(() => {
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setMenu(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const save = async () => {
    setSaving(true);
    try { await saveProfile(draft); toast("Profile saved — answers now use your context"); setProfileOpen(false); }
    catch (e) { toast(`Couldn't save: ${(e as Error).message}`); }
    setSaving(false);
  };

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <motion.button className="avatar" style={{ background: profile.color }} onClick={() => setMenu((m) => !m)}
        whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.94 }} aria-label="Profile">
        {profile.name ? initials(profile.name) : <UserRound size={18} color="#0a0d1f" />}
      </motion.button>

      <AnimatePresence>
        {menu && (
          <motion.div className="menu glass" initial={{ opacity: 0, y: -8, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }} transition={{ duration: 0.18 }}>
            <div className="row" style={{ padding: "8px 10px 12px" }}>
              <div className="avatar" style={{ background: profile.color, cursor: "default" }}>
                {profile.name ? initials(profile.name) : <UserRound size={18} color="#0a0d1f" />}
              </div>
              <div>
                <b>{profile.name || "Guest"}</b>
                <div className="faint small">{[profile.role, profile.team].filter(Boolean).join(" · ") || "Set up your profile"}</div>
              </div>
            </div>
            <label className="label" style={{ margin: "0 10px 6px" }}>Asking as</label>
            <div style={{ padding: "0 10px 8px" }}>
              <select className="select" value={persona} onChange={(e) => setPersona(e.target.value)}>
                {Object.entries(personas).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </div>
            <button className="menu-item" onClick={() => { setMenu(false); setProfileOpen(true); }}><Pencil size={16} /> Edit profile</button>
            <button className="menu-item" onClick={() => { setMenu(false); setSettingsOpen(true); }}><Settings size={16} /> Settings</button>
          </motion.div>
        )}
      </AnimatePresence>

      {mounted && createPortal(
      <AnimatePresence>
        {profileOpen && (
          <>
            <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setProfileOpen(false)} />
            <motion.div className="modal glass" initial={{ opacity: 0, scale: 0.92, x: "-50%", y: "-46%" }}
              animate={{ opacity: 1, scale: 1, x: "-50%", y: "-50%" }} exit={{ opacity: 0, scale: 0.94, x: "-50%", y: "-46%" }}
              transition={{ type: "spring", stiffness: 260, damping: 24 }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <h2 style={{ margin: 0 }}>Your profile</h2>
                <button className="icon-btn" onClick={() => setProfileOpen(false)} aria-label="Close"><X size={16} /></button>
              </div>
              <p className="muted small">Saved as your personal memory in HydraDB, so answers know who you are.</p>
              <div className="row" style={{ margin: "8px 0" }}>
                {COLORS.map((c) => (
                  <span key={c} className={`swatch ${draft.color === c ? "on" : ""}`} style={{ background: c }}
                    onClick={() => setDraft({ ...draft, color: c })} />
                ))}
              </div>
              <label className="label">Name</label>
              <input className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="Your name" />
              <div className="grid2">
                <div><label className="label">Role</label>
                  <input className="input" value={draft.role} onChange={(e) => setDraft({ ...draft, role: e.target.value })} placeholder="Engineer, PM, Founder…" /></div>
                <div><label className="label">Team</label>
                  <input className="input" value={draft.team} onChange={(e) => setDraft({ ...draft, team: e.target.value })} placeholder="Platform, Sales…" /></div>
              </div>
              <label className="label">About you (what should the brain remember?)</label>
              <textarea className="textarea" rows={3} value={draft.about} onChange={(e) => setDraft({ ...draft, about: e.target.value })}
                placeholder="I own the mobile release and prefer short answers with owners." />
              <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}>
                <button className="btn-ghost" onClick={() => setProfileOpen(false)}>Cancel</button>
                <button className="btn" onClick={save} disabled={saving}><Check size={16} /> {saving ? "Saving…" : "Save profile"}</button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
