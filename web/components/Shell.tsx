"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { Brain, Settings as SettingsIcon } from "lucide-react";
import type { ReactNode } from "react";
import { FEATURES, featureFor } from "../lib/features";
import { useStore } from "../lib/store";
import ProfileMenu from "./ProfileMenu";
import SettingsDrawer from "./SettingsDrawer";
import FeaturePanel from "./FeaturePanel";

function Backdrop() {
  const blobs = [
    { c: "var(--accent)", s: 520, x: ["-10%", "8%", "-10%"], y: ["-15%", "5%", "-15%"], d: 22 },
    { c: "var(--accent2)", s: 460, x: ["70%", "55%", "70%"], y: ["-10%", "15%", "-10%"], d: 26 },
    { c: "#22d3ee", s: 380, x: ["35%", "50%", "35%"], y: ["70%", "55%", "70%"], d: 30 },
  ];
  return (
    <div className="backdrop" aria-hidden>
      {blobs.map((b, i) => (
        <motion.div key={i} className="blob" style={{ width: b.s, height: b.s, background: b.c }}
          animate={{ left: b.x, top: b.y, scale: [1, 1.12, 1] }}
          transition={{ duration: b.d, repeat: Infinity, ease: "easeInOut" }} />
      ))}
      <div className="grid-overlay" />
    </div>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { settings, health, engineDown, setSettingsOpen, toastMsg } = useStore();
  const live = health?.mode === "hydradb";
  const current = featureFor(path);

  return (
    <MotionConfig reducedMotion={settings.reduceMotion ? "always" : "never"}>
      <Backdrop />
      <div className="shell">
        {/* ---------- top bar ---------- */}
        <motion.header className="topbar glass" initial={{ y: -30, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
          transition={{ type: "spring", stiffness: 120, damping: 18 }}>
          <Link href="/" className="brand">
            <motion.span className="brand-mark" whileHover={{ rotate: -8, scale: 1.08 }}><Brain size={20} color="#0a0d1f" /></motion.span>
            <span className="grad">WhyBot</span>
          </Link>
          <span className="status">
            <span className={`dot ${health ? (live ? "live" : "off") : engineDown ? "down" : ""}`} />
            {health ? (live ? "HydraDB live" : "Offline mode") : engineDown ? "Engine offline" : "Connecting…"}
          </span>
          <span className="status small" style={{ display: health ? undefined : "none" }}>
            {health?.docs ?? 0} docs · {health?.edges ?? 0} links
          </span>
          <div className="spacer" />
          <motion.button className="icon-btn" aria-label="Settings" onClick={() => setSettingsOpen(true)}
            whileHover={{ rotate: 60 }} whileTap={{ scale: 0.9 }}>
            <SettingsIcon size={18} />
          </motion.button>
          <ProfileMenu />
        </motion.header>

        <div className="body">
          {/* ---------- left: features ---------- */}
          <motion.nav className="rail glass" initial={{ x: -30, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.05, type: "spring", stiffness: 120, damping: 18 }}>
            <div className="rail-label">Features</div>
            {FEATURES.map((f, i) => {
              const on = f.href === current.href;
              const Icon = f.icon;
              return (
                <motion.div key={f.href} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.05 }}>
                  <Link href={f.href} className={`rail-item ${on ? "on" : ""}`}>
                    {on && <motion.span layoutId="rail-pill" className="pill-bg"
                      transition={{ type: "spring", stiffness: 380, damping: 32 }} />}
                    <Icon size={18} />
                    <span>{f.name}<small>{f.tagline}</small></span>
                  </Link>
                </motion.div>
              );
            })}
            <div className="rail-foot glass-soft">
              Built on <b className="grad">HydraDB</b>
              <div className="faint">Company Brain Hackathon</div>
            </div>
          </motion.nav>

          {/* ---------- center: the feature ---------- */}
          <main className="main">
            <AnimatePresence mode="wait">
              <motion.div key={path} initial={{ opacity: 0, y: 18, filter: "blur(6px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.35, ease: "easeOut" }}>
                {children}
              </motion.div>
            </AnimatePresence>
          </main>

          {/* ---------- right: details + workflow ---------- */}
          <motion.aside className="side glass" initial={{ x: 30, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.1, type: "spring", stiffness: 120, damping: 18 }}>
            <AnimatePresence mode="wait">
              <FeaturePanel key={current.href} feature={current} />
            </AnimatePresence>
          </motion.aside>
        </div>
      </div>

      <SettingsDrawer />
      <AnimatePresence>
        {toastMsg && (
          <motion.div className="toast glass" initial={{ y: 40, opacity: 0, x: "-50%" }}
            animate={{ y: 0, opacity: 1, x: "-50%" }} exit={{ y: 40, opacity: 0, x: "-50%" }}>
            {toastMsg}
          </motion.div>
        )}
      </AnimatePresence>
    </MotionConfig>
  );
}
