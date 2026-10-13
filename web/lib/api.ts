// Typed client for the WhyBot FastAPI backend (proxied at /api by next.config.mjs)

export type Chunk = { title: string; content: string; score: number | null };
export type Answer = {
  answer: string;
  chunks: Chunk[];
  paths: string[];
  memories: string[];
  mode: string;
  latency_ms: number;
  features: string[];
};
export type Health = {
  ok: boolean;
  mode: "mock" | "hydradb";
  database: string;
  docs: number;
  sample_loaded: boolean;
  questions: number;
  edges: number;
  starter_questions: string[];
  sample_questions: string[];
  public?: boolean;
};
export type Impact = {
  change: string; seeds: string[];
  affected: { name: string; hop: number; via: string }[];
  owners: Record<string, string[]>; people: string[]; incidents: string[];
  risk: { score: number; level: "Low" | "Medium" | "High" };
  brief: string; notify: { to: string; message: string }[];
  paths: string[]; chunks: Chunk[]; features: string[]; mode: string; latency_ms: number;
};
export type InventoryRow = { id: string; title: string; type: string; status?: string };
export type Persona = { label: string; memories: string[] };

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`/api${path}`, { cache: "no-store", ...init });
  } catch {
    throw new Error("Can't reach the WhyBot engine. Check that the backend is running.");
  }
  if (!r.ok) {
    const raw = await r.text();
    let msg: unknown = "";
    let fromEngine = false;
    try { const j = JSON.parse(raw); if (j && j.detail !== undefined) { msg = j.detail; fromEngine = true; } } catch {}
    if (Array.isArray(msg)) msg = msg.map((e) => (e && typeof e === "object" && "msg" in e ? (e as { msg: string }).msg : String(e))).join("; ");
    // A non-JSON 5xx comes from the Next.js proxy itself: the engine is down or unreachable.
    if (!fromEngine && r.status >= 500) msg = "Can't reach the WhyBot engine. Check that the backend is running on port 8000.";
    if (!fromEngine && r.status < 500) msg = raw.slice(0, 200);
    throw new Error(String(msg || r.statusText || `HTTP ${r.status}`).slice(0, 240));
  }
  return r.json();
}
const post = <T,>(path: string, body: unknown = {}) =>
  req<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  health: () => req<Health>("/health"),
  personas: () => req<Record<string, Persona>>("/personas/full"),
  inventory: () => req<InventoryRow[]>("/inventory"),
  graph: () => req<{ edges: string[] }>("/graph"),
  ask: (question: string, persona: string | null, graph: boolean) =>
    post<Answer>("/ask", { question, persona, graph }),
  compare: (question: string, persona: string | null) =>
    post<{ without_graph: Answer; with_graph: Answer }>("/compare", { question, persona }),
  impact: (change: string, persona: string | null) => post<Impact>("/impact", { change, persona }),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ ingested: string[] }>("/upload", { method: "POST", body: fd });
  },
  url: (url: string) => post<{ ingested: string[] }>("/url", { url }),
  sample: () => post<{ ingested: string[] }>("/sample"),
  memory: (persona: string, text: string) => post("/memory", { persona, text }),
  createPersona: (label: string, memories: string[]) => post<{ key: string }>("/persona", { label, memories }),
  profile: (p: { name: string; role: string; team: string; about: string }) =>
    post<{ persona: string }>("/profile", p),
  reset: () => post("/reset"),
};

export function parsePath(p: string): [string, string, string] | null {
  const m = p.match(/^(.+?) --\[(.+?)\]--> (.+)$/);
  return m ? [m[1], m[2], m[3]] : null;
}
