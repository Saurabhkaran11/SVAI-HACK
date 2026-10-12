"use client";
import { motion } from "motion/react";
import type { ReactNode } from "react";

export default function PageHead({ title, sub, children }: { title: ReactNode; sub: ReactNode; children?: ReactNode }) {
  return (
    <div className="glass page-head">
      <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>{title}</motion.h1>
      <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>{sub}</motion.p>
      {children}
    </div>
  );
}
