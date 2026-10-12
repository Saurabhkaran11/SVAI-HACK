"use client";
// App-wide state: settings, profile, current persona, backend health.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Health, type Persona } from "./api";

export type Settings = {
  accent: "indigo" | "violet" | "teal" | "rose";
  reduceMotion: boolean;
  compareDefault: boolean;
  graphDefault: boolean;
  blur: number;
  defaultPersona: string;
};
export type Profile = { name: string; role: string; team: string; about: string; color: string };

const DEFAULT_SETTINGS: Settings = {
  accent: "indigo", reduceMotion: false, compareDefault: true, graphDefault: true, blur: 18, defaultPersona: "engineer",
};
const DEFAULT_PROFILE: Profile = { name: "", role: "", team: "", about: "", color: "#7c8cff" };

export const ACCENTS: Record<Settings["accent"], [string, string]> = {
  indigo: ["#7c8cff", "#c084fc"],
  violet: ["#a78bfa", "#f472b6"],
  teal: ["#2dd4bf", "#60a5fa"],
  rose: ["#fb7185", "#fbbf24"],
};

type Ctx = {
  settings: Settings; setSettings: (s: Partial<Settings>) => void;
  profile: Profile; saveProfile: (p: Profile) => Promise<void>;
  persona: string; setPersona: (p: string) => void;
  personas: Record<string, Persona>; refreshPersonas: () => Promise<void>;
  health: Health | null; engineDown: boolean; refreshHealth: () => Promise<void>;
  toast: (msg: string) => void; toastMsg: string | null;
  settingsOpen: boolean; setSettingsOpen: (v: boolean) => void;
  profileOpen: boolean; setProfileOpen: (v: boolean) => void;
};
const C = createContext<Ctx | null>(null);

function load<T>(key: string, fallback: T): T {
  try { const v = localStorage.getItem(key); return v ? { ...fallback, ...JSON.parse(v) } : fallback; } catch { return fallback; }
}
function save(key: string, v: unknown) { try { localStorage.setItem(key, JSON.stringify(v)); } catch {} }

export function StoreProvider({ children }: { children: ReactNode }) {
  const [settings, _setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [profile, setProfile] = useState<Profile>(DEFAULT_PROFILE);
  const [persona, _setPersona] = useState("engineer");
  const [personas, setPersonas] = useState<Record<string, Persona>>({});
  const [health, setHealth] = useState<Health | null>(null);
  const [engineDown, setEngineDown] = useState(false);
  const [toastMsg, setToast] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const toast = useCallback((m: string) => {
    setToast(m);
    window.setTimeout(() => setToast((cur) => (cur === m ? null : cur)), 2800);
  }, []);
  const refreshHealth = useCallback(async () => {
    try { setHealth(await api.health()); setEngineDown(false); } catch { setHealth(null); setEngineDown(true); }
  }, []);
  const refreshPersonas = useCallback(async () => {
    try { setPersonas(await api.personas()); } catch {}
  }, []);

  useEffect(() => {
    const s = load("wb.settings", DEFAULT_SETTINGS);
    _setSettings(s);
    setProfile(load("wb.profile", DEFAULT_PROFILE));
    _setPersona(localStorage.getItem("wb.persona") || s.defaultPersona);
    refreshHealth(); refreshPersonas();
    const t = window.setInterval(refreshHealth, 15000);
    return () => window.clearInterval(t);
  }, [refreshHealth, refreshPersonas]);

  // apply theme settings as CSS variables
  useEffect(() => {
    const [a, b] = ACCENTS[settings.accent];
    const r = document.documentElement.style;
    r.setProperty("--accent", a); r.setProperty("--accent2", b); r.setProperty("--blur", `${settings.blur}px`);
  }, [settings.accent, settings.blur]);

  const setSettings = (p: Partial<Settings>) => _setSettings((cur) => { const n = { ...cur, ...p }; save("wb.settings", n); return n; });
  const setPersona = (p: string) => { _setPersona(p); try { localStorage.setItem("wb.persona", p); } catch {} };
  const saveProfile = async (p: Profile) => {
    setProfile(p); save("wb.profile", p);
    const r = await api.profile({ name: p.name, role: p.role, team: p.team, about: p.about });
    await refreshPersonas(); setPersona(r.persona);
  };

  return (
    <C.Provider value={{ settings, setSettings, profile, saveProfile, persona, setPersona, personas, refreshPersonas,
      health, engineDown, refreshHealth, toast, toastMsg, settingsOpen, setSettingsOpen, profileOpen, setProfileOpen }}>
      {children}
    </C.Provider>
  );
}

export const useStore = () => {
  const c = useContext(C);
  if (!c) throw new Error("useStore outside provider");
  return c;
};
