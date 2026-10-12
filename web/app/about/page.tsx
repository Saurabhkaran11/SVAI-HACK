"use client";
import { motion } from "motion/react";
import { Zap, Layers, Megaphone, ExternalLink, Users } from "lucide-react";
import PageHead from "../../components/PageHead";

const CARDS = [
  {
    icon: Zap, title: "HydraDB", sub: "The memory layer behind every answer",
    points: ["Hybrid search — semantic + keyword in one call", "Context graphs — multi-hop paths across people, services, decisions",
      "Bring-your-own-graph — exact edges for org charts and service catalogs", "Memories — one collection per persona, merged via type=\"all\"",
      "Thinking mode — query expansion for deeper traversal"],
    links: [["Get a key", "https://app.hydradb.com/sign-up"], ["Docs", "https://docs.hydradb.com/"]],
  },
  {
    icon: Layers, title: "App-Starter", sub: "The SaaS shell",
    points: ["WhyBot's REST API drops into App-Starter for auth, billing and team workspaces",
      "Each workspace maps to a HydraDB database; each user to a memory collection", "Ship a paid company-brain product in days"],
    links: [],
  },
  {
    icon: Megaphone, title: "Digo", sub: "Company Brain Hackathon host",
    points: ["Built in one afternoon at the Company Brain Hackathon", "Real files, real docs sites, live on stage"],
    links: [["Digo", "https://digo.com"]],
  },
];

const WHO = [
  ["New hires", "Who owns what and who to ask — onboarding in days, not weeks"],
  ["Engineers", "What breaks if I change this? Fewer incidents"],
  ["Managers", "What's blocking us, and who's on it?"],
  ["Support", "Answers from tickets and runbooks"],
  ["Anyone", "A personal brain from notes and PDFs"],
];

export default function AboutPage() {
  return (
    <>
      <PageHead title={<>Built <span className="grad">with</span></>}
        sub="WhyBot = HydraDB memory + Claude reasoning + a Next.js and FastAPI product, ready to become a SaaS on App-Starter." />
      <div className="grid3">
        {CARDS.map((c, i) => {
          const Icon = c.icon;
          return (
            <motion.div key={c.title} className="glass card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }} whileHover={{ y: -6 }} style={{ marginBottom: 0 }}>
              <div className="feat-icon"><Icon size={22} /></div>
              <h2 style={{ margin: "12px 0 2px" }}>{c.title}</h2>
              <div className="faint small">{c.sub}</div>
              <ul className="small muted" style={{ paddingLeft: 18, lineHeight: 1.6 }}>{c.points.map((p) => <li key={p}>{p}</li>)}</ul>
              <div className="row wrap">{c.links.map(([t, h]) => (
                <a key={h} className="btn-ghost small" href={h} target="_blank" rel="noreferrer">{t} <ExternalLink size={13} /></a>
              ))}</div>
            </motion.div>
          );
        })}
      </div>

      <div className="glass card" style={{ marginTop: 14 }}>
        <h3><Users size={14} style={{ verticalAlign: -2 }} /> Who it's for</h3>
        <div className="grid3">
          {WHO.map(([t, d], i) => (
            <motion.div key={t} className="glass-soft" style={{ padding: 14 }} initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 + i * 0.05 }}>
              <b>{t}</b><div className="muted small">{d}</div>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="glass card">
        <h3>Business model</h3>
        <div className="grid3">
          {[["Free", "$0", "Personal brain · 1 user · 100 docs"], ["Team", "$15/seat/mo", "Slack, Notion, Jira connectors · shared personas"],
            ["Enterprise", "Custom", "SSO · private HydraDB · audit logs"]].map(([t, p, d], i) => (
            <motion.div key={t} className="glass-soft" style={{ padding: 16 }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.06 }}>
              <b>{t}</b><div className="grad" style={{ fontSize: 22, fontWeight: 800 }}>{p}</div><div className="muted small">{d}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </>
  );
}
