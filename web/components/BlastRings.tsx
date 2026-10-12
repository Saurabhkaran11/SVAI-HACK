"use client";
import { motion } from "motion/react";
import type { Impact } from "../lib/api";

// Animated "shockwave": the change at the centre, affected systems on rings by hop distance.
export default function BlastRings({ impact }: { impact: Impact }) {
  const size = 520, c = size / 2;
  const radii = [0, 95, 165, 230];
  const color = "#2563eb";
  const byHop = new Map<number, typeof impact.affected>();
  impact.affected.forEach((a) => byHop.set(a.hop, [...(byHop.get(a.hop) ?? []), a]));
  const placed: { name: string; x: number; y: number; hop: number }[] = [];
  byHop.forEach((list, hop) => {
    if (hop === 0) return;
    list.forEach((a, i) => {
      const ang = (i / list.length) * Math.PI * 2 - Math.PI / 2 + hop * 0.5;
      placed.push({ name: a.name, hop, x: c + Math.cos(ang) * radii[hop], y: c + Math.sin(ang) * radii[hop] });
    });
  });
  const centre = impact.seeds.length ? impact.seeds.join(", ") : "your change";

  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: "100%", maxHeight: 520 }}>
      <defs>
        <radialGradient id="core"><stop offset="0%" stopColor={color} stopOpacity="0.18" /><stop offset="100%" stopColor={color} stopOpacity="0" /></radialGradient>
      </defs>
      {[1, 2, 3].map((h) => (
        <motion.circle key={h} cx={c} cy={c} r={radii[h]} fill="none" stroke="#d1d5db" strokeDasharray="4 6"
          initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.15 * h, duration: 0.6 }}
          style={{ transformOrigin: `${c}px ${c}px` }} />
      ))}
      {[0, 1, 2].map((i) => (
        <motion.circle key={`w${i}`} cx={c} cy={c} r={40} fill="none" stroke={color} strokeWidth={2}
          initial={{ scale: 0.4, opacity: 0.8 }} animate={{ scale: 6, opacity: 0 }}
          transition={{ duration: 3, delay: i, repeat: Infinity, ease: "easeOut" }} style={{ transformOrigin: `${c}px ${c}px` }} />
      ))}
      {placed.map((p, i) => (
        <motion.line key={`l${p.name}`} x1={c} y1={c} x2={p.x} y2={p.y} stroke={color} strokeOpacity={0.35}
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.4 + i * 0.08, duration: 0.5 }} />
      ))}
      <circle cx={c} cy={c} r={70} fill="url(#core)" />
      <motion.circle cx={c} cy={c} r={34} fill={color} initial={{ scale: 0 }} animate={{ scale: [0, 1.2, 1] }}
        transition={{ duration: 0.6 }} style={{ transformOrigin: `${c}px ${c}px` }} />
      <text x={c} y={c + 58} textAnchor="middle" fill="#111827" fontSize="14" fontWeight="700">{centre.slice(0, 32)}</text>
      {placed.map((p, i) => (
        <motion.g key={p.name} initial={{ opacity: 0, scale: 0 }} animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6 + i * 0.1, type: "spring", stiffness: 200, damping: 14 }} style={{ transformOrigin: `${p.x}px ${p.y}px` }}>
          <circle cx={p.x} cy={p.y} r={p.hop === 1 ? 11 : 8} fill={color} fillOpacity={p.hop === 1 ? 0.95 : 0.6} stroke="#fff" strokeOpacity={0.6} />
          <text x={p.x} y={p.y - 16} textAnchor="middle" fill="#374151" fontSize="12.5">{p.name}</text>
        </motion.g>
      ))}
      {[1, 2, 3].map((h) => (
        <text key={`t${h}`} x={c + radii[h] - 4} y={c - 6} textAnchor="end" fill="#9ca3af" fontSize="10">hop {h}</text>
      ))}
    </svg>
  );
}
