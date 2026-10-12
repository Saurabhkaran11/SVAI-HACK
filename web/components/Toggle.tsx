"use client";
import { motion } from "motion/react";

export default function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label}
      className={`toggle ${on ? "on" : ""}`} onClick={() => onChange(!on)}>
      <motion.span className="knob" layout transition={{ type: "spring", stiffness: 500, damping: 32 }} />
    </button>
  );
}
