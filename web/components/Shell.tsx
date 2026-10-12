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

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { settings, health, engineDown, setSettingsOpen, toastMsg } = useStore();
  const live = health?.mode === "hydradb";
  const current = featureFor(path);

  return (
    <MotionConfig reducedMotion={settings.reduceMotion ? "always" : "never"}>
      <div className="shell">
        {/* ---------- top bar ---------- */}
        <header className="topbar glass">
          <Link href="/" className="brand">
            <motion.span className="brand-mark" ><Brain size={18} color="#fff" /></motion.span>
            <span>WhyBot</span>
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
            >
            <SettingsIcon size={18} />
          </motion.button>
          <ProfileMenu />
        </header>

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
              Built on <b>HydraDB</b>
              <div className="faint">Company Brain Hackathon</div>
            </div>
          </motion.nav>

          {/* ---------- center: the feature ---------- */}
          <main className="main">
            <AnimatePresence mode="wait">
              <motion.div key={path} initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}>
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
