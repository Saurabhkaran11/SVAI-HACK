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
      const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#2563eb";
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
              color: { background: hit ? accent : "#ffffff", border: hit ? accent : "#cbd2dc", highlight: { background: "#eff4ff", border: accent }, hover: { background: "#eff4ff", border: accent } },
              font: { color: hit ? "#ffffff" : "#111827", size: 15 },
            });
          }
        }
        edges.push({ from: a, to: b, label: rel });
      });
      const n = new Network(ref.current, { nodes: new DataSet([...nodes.values()]), edges: new DataSet(edges as never[]) }, {
        nodes: { shape: "box", margin: { top: 10, bottom: 10, left: 12, right: 12 }, borderWidth: 1.5, shapeProperties: { borderRadius: 10 } },
        edges: { arrows: "to", color: { color: "#9ca3af", highlight: accent, hover: accent }, font: { color: "#6b7280", size: 11, strokeWidth: 3, strokeColor: "#f7f8fa", align: "middle" },
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
