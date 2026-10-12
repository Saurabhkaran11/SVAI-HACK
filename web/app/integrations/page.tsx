"use client";
import { useState } from "react";
import { motion } from "motion/react";
import { Play, Copy, ExternalLink } from "lucide-react";
import PageHead from "../../components/PageHead";
import { useStore } from "../../lib/store";

type Ep = { method: "GET" | "POST"; path: string; desc: string; body?: object };
const ENDPOINTS: Ep[] = [
  { method: "POST", path: "/ask", desc: "Answer a question (graph + persona)", body: { question: "Who owns what?", persona: "new_hire", graph: true } },
  { method: "POST", path: "/compare", desc: "Plain search vs graph answer", body: { question: "What are the biggest risks?", persona: "manager" } },
  { method: "POST", path: "/url", desc: "Ingest a public web page", body: { url: "https://docs.hydradb.com/" } },
  { method: "POST", path: "/memory", desc: "Remember a fact for a persona", body: { persona: "engineer", text: "I own the payments SDK" } },
  { method: "GET", path: "/graph", desc: "Every known relationship" },
  { method: "GET", path: "/inventory", desc: "Documents + indexing status" },
  { method: "GET", path: "/health", desc: "Engine status and counts" },
];

export default function IntegrationsPage() {
  const { toast, refreshHealth } = useStore();
  const [sel, setSel] = useState(0);
  const [body, setBody] = useState(JSON.stringify(ENDPOINTS[0].body, null, 2));
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);
  const ep = ENDPOINTS[sel];

  const pick = (i: number) => { setSel(i); setBody(ENDPOINTS[i].body ? JSON.stringify(ENDPOINTS[i].body, null, 2) : ""); setOut(""); };
  const run = async () => {
    setBusy(true); setOut("");
    try {
      const r = await fetch(`/api${ep.path}`, ep.method === "POST"
        ? { method: "POST", headers: { "Content-Type": "application/json" }, body: body || "{}" } : undefined);
      const text = await r.text();
      try { setOut(JSON.stringify(JSON.parse(text), null, 2)); } catch { setOut(text); }
      refreshHealth();
    } catch (e) { setOut(String(e)); }
    setBusy(false);
  };
  const curl = `curl -X ${ep.method} http://localhost:8000${ep.path}` +
    (ep.method === "POST" ? ` \\\n  -H "Content-Type: application/json" \\\n  -d '${(body || "{}").replace(/\s+/g, " ")}'` : "");
  const slack = `// Slack bot: answer /why commands with WhyBot
app.command("/why", async ({ command, ack, respond }) => {
  await ack();
  const r = await fetch("http://localhost:8000/ask", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: command.text, persona: "new_hire" }),
  }).then((x) => x.json());
  await respond(r.answer);
});`;
  const copy = (t: string) => { navigator.clipboard?.writeText(t); toast("Copied"); };

  return (
    <>
      <PageHead title={<>API & <span className="grad">integrations</span></>}
        sub="One REST API powers this app. Use it from a Slack bot, an App-Starter SaaS frontend, an IDE plugin or an internal portal.">
        <a className="btn-ghost" style={{ marginTop: 14 }} href="/api/docs" target="_blank" rel="noreferrer">Full API reference <ExternalLink size={14} /></a>
      </PageHead>

      <div className="grid2">
        <div className="glass card">
          <h3>Endpoints</h3>
          {ENDPOINTS.map((e, i) => (
            <motion.button key={e.path} className="menu-item" onClick={() => pick(i)} whileHover={{ x: 4 }}
              style={{ background: i === sel ? "rgba(124,140,255,.16)" : undefined }}>
              <span className="tag" style={{ margin: 0, minWidth: 50, justifyContent: "center",
                background: e.method === "GET" ? "rgba(52,211,153,.12)" : undefined, color: e.method === "GET" ? "#a7f3d0" : undefined }}>{e.method}</span>
              <code>{e.path}</code><span className="faint small">{e.desc}</span>
            </motion.button>
          ))}
        </div>

        <div className="glass card">
          <h3>Try it live</h3>
          <div className="row"><span className="tag" style={{ margin: 0 }}>{ep.method}</span><code>{ep.path}</code></div>
          {ep.method === "POST" && (
            <textarea className="textarea" rows={5} style={{ marginTop: 10, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 13 }}
              value={body} onChange={(e) => setBody(e.target.value)} />
          )}
          <button className="btn" style={{ marginTop: 10 }} onClick={run} disabled={busy}><Play size={14} /> {busy ? "Running…" : "Send request"}</button>
          {out && <motion.pre className="codeblock" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>{out}</motion.pre>}
        </div>
      </div>

      <div className="grid2" style={{ marginTop: 14 }}>
        <div className="glass card">
          <div className="row" style={{ justifyContent: "space-between" }}><h3 style={{ margin: 0 }}>cURL</h3>
            <button className="btn-ghost small" onClick={() => copy(curl)}><Copy size={14} /> Copy</button></div>
          <pre className="codeblock">{curl}</pre>
        </div>
        <div className="glass card">
          <div className="row" style={{ justifyContent: "space-between" }}><h3 style={{ margin: 0 }}>Slack bot (Bolt.js)</h3>
            <button className="btn-ghost small" onClick={() => copy(slack)}><Copy size={14} /> Copy</button></div>
          <pre className="codeblock">{slack}</pre>
        </div>
      </div>
    </>
  );
}
