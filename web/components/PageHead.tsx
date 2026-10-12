"use client";
import { motion } from "motion/react";
import type { ReactNode } from "react";

export default function PageHead({ title, sub, children }: { title: ReactNode; sub: ReactNode; children?: ReactNode }) {
  return (
    <div className="glass page-head">
      <motion.div aria-hidden style={{ position: "absolute", right: -60, top: -80, width: 260, height: 260, borderRadius: "50%",
        background: "radial-gradient(circle, var(--accent2), transparent 70%)", opacity: 0.35 }}
        animate={{ scale: [1, 1.15, 1], rotate: [0, 30, 0] }} transition={{ duration: 10, repeat: Infinity }} />
      <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>{title}</motion.h1>
      <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>{sub}</motion.p>
      {children}
    </div>
  );
}
