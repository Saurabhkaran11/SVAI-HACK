"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { ZoomIn, ZoomOut, Maximize2, Pause, Play, X, Radar, ArrowRight, ArrowLeft } from "lucide-react";
import { parsePath } from "../lib/api";

// Interactive relationship graph (vis-network, client-side only).
// Hover traces a node's neighbours, click opens its details, drag rearranges with live physics.
type Props = { paths: string[]; height?: number; focus?: string; explorer?: boolean };
type Triple = [string, string, string];

const C = {
  accent: "#2563eb", soft: "#eff4ff", ink: "#111827", muted: "#6b7280",
  line: "#b8c0cc", node: "#ffffff", border: "#cbd2dc", fadeFill: "#f7f8fa", fadeInk: "#c3c9d3", fadeLine: "#eceef2",
};
const ease = { duration: 650, easingFunction: "easeInOutCubic" as const };
const pretty = (r: string) => r.replace(/_/g, " ").toLowerCase();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export default function GraphView({ paths, height = 380, focus = "", explorer = false }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const net = useRef<Any>(null);
  const data = useRef<{ nodes: Any; edges: Any } | null>(null);
  const selRef = useRef<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [physics, setPhysics] = useState(true);
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const g = useMemo(() => {
    const seen = new Map<string, Triple>();
    paths.forEach((p) => { const t = parsePath(p); if (t) seen.set(t.join("|"), t as Triple); });
    const triples = [...seen.values()].slice(0, 160);
    const deg = new Map<string, number>(), rels = new Map<string, number>();
    triples.forEach(([a, r, b]) => {
      deg.set(a, (deg.get(a) ?? 0) + 1); deg.set(b, (deg.get(b) ?? 0) + 1); rels.set(r, (rels.get(r) ?? 0) + 1);
    });
    return { triples, deg, rels: [...rels.entries()].sort((x, y) => y[1] - x[1]) };
  }, [paths]);

  const visible = useMemo(() => g.triples.filter(([, r]) => !hidden.has(r)), [g, hidden]);

  // ---- highlight helpers -------------------------------------------------------------
  const paint = (center: string | null, keep?: Set<string>) => {
    const d = data.current, n = net.current;
    if (!d || !n) return;
    const near = keep ?? (center ? new Set<string>([center, ...n.getConnectedNodes(center)]) : null);
    d.nodes.update(d.nodes.getIds().map((id: string) => {
      const on = !near || near.has(id), main = id === center;
      return {
        id,
        color: { background: main ? C.accent : on ? C.node : C.fadeFill, border: main || (on && near) ? C.accent : on ? C.border : C.fadeLine,
          hover: { background: main ? C.accent : C.soft, border: C.accent }, highlight: { background: C.accent, border: C.accent } },
        font: { color: main ? "#ffffff" : on ? C.ink : C.fadeInk },
      };
    }));
    d.edges.update(d.edges.get().map((e: Any) => {
      const on = !near || (near.has(e.from) && near.has(e.to) && (!center || e.from === center || e.to === center || !!keep));
      return { id: e.id, color: { color: near && on ? C.accent : on ? C.line : C.fadeLine, highlight: C.accent, hover: C.accent },
        font: { color: on ? (near ? C.accent : C.muted) : "rgba(0,0,0,0)" }, width: near && on ? 1.8 : 1.1 };
    }));
  };

  const select = (id: string | null) => {
    selRef.current = id; setSelected(id);
    paint(id);
    // wait for the details panel to open (the canvas narrows), then glide to the node and its neighbours
    window.setTimeout(() => {
      const n = net.current;
      if (!n) return;
      n.redraw();
      if (id) n.fit({ nodes: [id, ...n.getConnectedNodes(id)], maxZoomLevel: 1.3, animation: ease });
      else n.fit({ animation: ease });
    }, 320);
  };

  // ---- build the network --------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [{ Network }, { DataSet }] = await Promise.all([import("vis-network/standalone"), import("vis-data/standalone")]);
      if (cancelled || !box.current) return;
      const names = new Set<string>();
      visible.forEach(([a, , b]) => { names.add(a); names.add(b); });
      const nodes = new DataSet([...names].map((id) => {
        const d = g.deg.get(id) ?? 1;
        return { id, label: id, mass: 1 + d * 0.4, font: { size: 13 + Math.min(d, 6) * 1.1, face: "Inter, system-ui, sans-serif", color: C.ink },
          margin: { top: 9, bottom: 9, left: 12, right: 12 },
          color: { background: C.node, border: C.border, hover: { background: C.soft, border: C.accent }, highlight: { background: C.accent, border: C.accent } } };
      }));
      const edges = new DataSet(visible.map(([a, r, b]) => ({
        id: `${a}|${r}|${b}`, from: a, to: b, label: pretty(r), rel: r,
      })));
      data.current = { nodes, edges };
      net.current?.destroy();
      const n = new Network(box.current, { nodes, edges } as Any, {
        nodes: { shape: "box", borderWidth: 1.2, borderWidthSelected: 2, shapeProperties: { borderRadius: 8 },
          shadow: { enabled: true, color: "rgba(16,24,40,0.08)", size: 6, x: 0, y: 2 } },
        edges: { arrows: { to: { enabled: true, scaleFactor: 0.6 } }, width: 1.1, selectionWidth: 1, hoverWidth: 0.4,
          color: { color: C.line, highlight: C.accent, hover: C.accent },
          font: { size: 10.5, color: C.muted, strokeWidth: 4, strokeColor: "#f7f8fa", align: "middle" },
          smooth: { enabled: true, type: "continuous", roundness: 0.35 } },
        physics: { solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -70, springLength: 140, springConstant: 0.06, avoidOverlap: 0.7 },
          maxVelocity: 35, minVelocity: 0.6, stabilization: { enabled: true, iterations: 80, fit: true } },
        interaction: { hover: true, tooltipDelay: 120, zoomView: true, dragView: true, dragNodes: true, keyboard: false },
      });
      n.on("hoverNode", (p: Any) => { if (!selRef.current) paint(p.node); box.current && (box.current.style.cursor = "pointer"); });
      n.on("blurNode", () => { if (!selRef.current) paint(null); box.current && (box.current.style.cursor = "grab"); });
      n.on("click", (p: Any) => {
        if (p.nodes?.length) select(p.nodes[0]);
        else if (!p.edges?.length) select(null);
      });
      n.once("stabilizationIterationsDone", () => n.fit({ animation: ease }));
      net.current = n;
      selRef.current = null; setSelected(null); setPhysics(true);
    })();
    return () => { cancelled = true; net.current?.destroy(); net.current = null; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  // ---- focus from the search box: light up matches + neighbours, glide to them -------
  useEffect(() => {
    const n = net.current, d = data.current;
    if (!n || !d) return;
    const f = focus.trim().toLowerCase();
    if (!f) { if (!selRef.current) { paint(null); n.fit({ animation: ease }); } return; }
    const hits: string[] = d.nodes.getIds().filter((id: string) => id.toLowerCase().includes(f));
    if (!hits.length) return;
    const keep = new Set<string>(hits);
    hits.forEach((h) => n.getConnectedNodes(h).forEach((x: string) => keep.add(x)));
    selRef.current = null; setSelected(null);
    paint(hits.length === 1 ? hits[0] : null, keep);
    n.fit({ nodes: [...keep], animation: ease });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus, visible]);

  const zoom = (k: number) => net.current?.moveTo({ scale: net.current.getScale() * k, animation: { duration: 300, easingFunction: "easeOutQuad" } });
  const togglePhysics = () => { const on = !physics; setPhysics(on); net.current?.setOptions({ physics: { enabled: on } }); };
  const toggleRel = (r: string) => setHidden((h) => { const x = new Set(h); if (x.has(r)) x.delete(r); else x.add(r); return x; });

  const out = selected ? visible.filter(([a]) => a === selected) : [];
  const inc = selected ? visible.filter(([, , b]) => b === selected) : [];
  const nodeCount = new Set(visible.flatMap(([a, , b]) => [a, b])).size;

  return (
    <div className="gx">
      {explorer && (
        <div className="gx-bar">
          <div className="gx-rels">
            {g.rels.map(([r, c]) => (
              <button key={r} className={`gx-rel ${hidden.has(r) ? "off" : ""}`} onClick={() => toggleRel(r)} aria-pressed={!hidden.has(r)}>
                {pretty(r)} <span>{c}</span>
              </button>
            ))}
          </div>
          <div className="gx-tools">
            <button className="icon-btn" onClick={() => zoom(1.25)} aria-label="Zoom in" title="Zoom in"><ZoomIn size={16} /></button>
            <button className="icon-btn" onClick={() => zoom(0.8)} aria-label="Zoom out" title="Zoom out"><ZoomOut size={16} /></button>
            <button className="icon-btn" onClick={() => select(null)} aria-label="Fit to screen" title="Fit to screen"><Maximize2 size={16} /></button>
            <button className="icon-btn" onClick={togglePhysics} aria-label={physics ? "Freeze layout" : "Resume layout"} title={physics ? "Freeze layout" : "Resume layout"}>
              {physics ? <Pause size={16} /> : <Play size={16} />}
            </button>
          </div>
        </div>
      )}

      <div className={`gx-stage ${explorer && selected ? "with-panel" : ""}`}>
        <div className="gx-canvas-wrap">
          <div ref={box} className="graph-box gx-canvas" style={{ height, cursor: "grab" }} />
          <div className="gx-hint">{nodeCount} nodes · {visible.length} links · hover to trace · click for details · drag to rearrange</div>
        </div>

        <AnimatePresence>
          {explorer && selected && (
            <motion.aside className="gx-panel" key={selected} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 24 }} transition={{ duration: 0.25, ease: "easeOut" }} style={{ maxHeight: height }}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div className="faint small">Selected</div>
                  <h4>{selected}</h4>
                  <div className="muted small">{out.length + inc.length} {out.length + inc.length === 1 ? "connection" : "connections"}</div>
                </div>
                <button className="icon-btn" onClick={() => select(null)} aria-label="Close details"><X size={14} /></button>
              </div>
              <Link className="btn gx-cta" href={`/impact?change=${encodeURIComponent(`Deprecate ${selected}`)}`}>
                <Radar size={15} /> Check blast radius
              </Link>
              {out.length > 0 && <div className="gx-sec">Depends on / points to</div>}
              {out.map(([, r, b]) => (
                <button key={`o${r}${b}`} className="gx-link" onClick={() => select(b)}>
                  <ArrowRight size={13} /><span className="gx-rel-word">{pretty(r)}</span><b>{b}</b>
                </button>
              ))}
              {inc.length > 0 && <div className="gx-sec">Used by / pointed at by</div>}
              {inc.map(([a, r]) => (
                <button key={`i${a}${r}`} className="gx-link" onClick={() => select(a)}>
                  <ArrowLeft size={13} /><b>{a}</b><span className="gx-rel-word">{pretty(r)}</span>
                </button>
              ))}
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
