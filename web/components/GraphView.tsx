"use client";
import { useEffect, useRef } from "react";
import { parsePath } from "../lib/api";

// Interactive relationship graph (vis-network), loaded client-side only.
export default function GraphView({ paths, height = 380, focus = "" }: { paths: string[]; height?: number; focus?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let net: { destroy: () => void } | null = null;
    let cancelled = false;
    (async () => {
      const [{ Network }, { DataSet }] = await Promise.all([import("vis-network/standalone"), import("vis-data/standalone")]);
      if (cancelled || !ref.current) return;
      const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#7c8cff";
      const nodes = new Map<string, { id: string; label: string; color?: object; font?: object }>();
      const edges: { from: string; to: string; label: string }[] = [];
      const f = focus.trim().toLowerCase();
      paths.slice(0, 80).forEach((p) => {
        const t = parsePath(p);
        if (!t) return;
        const [a, rel, b] = t;
        if (f && !a.toLowerCase().includes(f) && !b.toLowerCase().includes(f)) return;
        for (const n of [a, b]) {
          if (!nodes.has(n)) {
            const hit = f && n.toLowerCase().includes(f);
            nodes.set(n, {
              id: n, label: n,
              color: { background: hit ? accent : "rgba(124,140,255,0.18)", border: accent, highlight: { background: accent, border: "#fff" } },
              font: { color: hit ? "#0a0d1f" : "#eef1ff", size: 16 },
            });
          }
        }
        edges.push({ from: a, to: b, label: rel });
      });
      const n = new Network(ref.current, { nodes: new DataSet([...nodes.values()]), edges: new DataSet(edges as never[]) }, {
        nodes: { shape: "box", margin: { top: 10, bottom: 10, left: 12, right: 12 }, borderWidth: 1.5, shapeProperties: { borderRadius: 10 } },
        edges: { arrows: "to", color: { color: accent, opacity: 0.8 }, font: { color: "#c7cffd", size: 12, strokeWidth: 0, align: "middle" },
          smooth: { enabled: true, type: "dynamic", roundness: 0.5 }, length: 180 },
        physics: { solver: "forceAtlas2Based", stabilization: { iterations: 220 } },
        interaction: { hover: true, zoomView: true, dragNodes: true },
      });
      n.once("stabilizationIterationsDone", () => { n.setOptions({ physics: false }); n.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } }); });
      net = n;
    })();
    return () => { cancelled = true; net?.destroy(); };
  }, [paths, focus]);

  return <div ref={ref} className="graph-box" style={{ height }} />;
}
