"use client";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Zap } from "lucide-react";
import type { Feature } from "../lib/features";

// Right panel: what the current feature does + an animated, auto-playing workflow.
export default function FeaturePanel({ feature }: { feature: Feature }) {
  const [active, setActive] = useState(0);
  const n = feature.workflow.length;
  useEffect(() => {
    setActive(0);
    const t = window.setInterval(() => setActive((a) => (a + 1) % n), 1800);
    return () => window.clearInterval(t);
  }, [feature.href, n]);
  const Icon = feature.icon;

  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}>
      <motion.div className="feat-icon" initial={{ scale: 0.6, rotate: -20 }} animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", stiffness: 220, damping: 14 }}>
        <Icon size={22} />
      </motion.div>
      <h2>{feature.name}</h2>
      <p className="muted small" style={{ lineHeight: 1.55 }}>{feature.details}</p>

      <div className="card glass-soft" style={{ padding: 16, marginTop: 16 }}>
        <h3 style={{ marginBottom: 4 }}>Workflow</h3>
        <div className="steps">
          {feature.workflow.map((s, i) => (
            <motion.div key={s.title} className={`step ${i === active ? "active" : ""}`}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: i <= active ? 1 : 0.55, y: 0 }}
              transition={{ delay: 0.08 * i }} onMouseEnter={() => setActive(i)}>
              {i < n - 1 && (
                <div className="step-line">
                  <motion.div className="fill" animate={{ height: i < active ? "100%" : "0%" }} transition={{ duration: 0.5 }} />
                </div>
              )}
              <motion.div className="step-num" animate={i === active ? { scale: [1, 1.15, 1] } : { scale: 1 }}
                transition={{ duration: 0.6 }}>{i + 1}</motion.div>
              <div><b>{s.title}</b><p>{s.text}</p></div>
            </motion.div>
          ))}
        </div>
      </div>

      <h3 className="faint" style={{ fontSize: 12, letterSpacing: ".12em", textTransform: "uppercase", margin: "18px 0 6px" }}>
        Powered by HydraDB
      </h3>
      <div>
        {feature.powered.map((p, i) => (
          <motion.span key={p} className="tag" initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 + i * 0.06 }}><Zap size={12} />{p}</motion.span>
        ))}
      </div>
    </motion.div>
  );
}
