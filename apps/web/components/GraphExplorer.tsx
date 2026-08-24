"use client";

import { useMemo } from "react";
import { ReactFlow, Background, Node, Edge, MarkerType, Position } from "@xyflow/react";
import { Snapshot, epistemicColor, severityColor } from "@/lib/api";

interface Props {
  snapshot: Snapshot;
  degradation: Record<string, number>; // node degradation at current time
  hiddenEdgeIds: string[];
  incidentTargets: string[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  layerFilter: Record<string, boolean>; // epistemic status -> visible
}

/** Deterministic layered layout: capability on the left, dependencies by BFS depth. */
function layout(snapshot: Snapshot): Record<string, { x: number; y: number }> {
  const depth: Record<string, number> = {};
  const capIds = snapshot.capabilities.map((c) => c.capability_id);
  capIds.forEach((id) => (depth[id] = 0));
  const out: Record<string, string[]> = {};
  snapshot.edges.forEach((e) => {
    (out[e.from_node] ??= []).push(e.to_node);
  });
  let frontier = [...capIds];
  let d = 0;
  const seen = new Set(frontier);
  while (frontier.length) {
    d += 1;
    const next: string[] = [];
    frontier.forEach((n) =>
      (out[n] ?? []).forEach((m) => {
        if (!seen.has(m)) {
          seen.add(m);
          depth[m] = d;
          next.push(m);
        }
      }),
    );
    frontier = next.sort();
  }
  snapshot.nodes.forEach((n) => {
    if (!(n.node_id in depth)) depth[n.node_id] = d + 1;
  });

  const byDepth: Record<number, string[]> = {};
  Object.entries(depth).forEach(([id, dd]) => (byDepth[dd] ??= []).push(id));
  const pos: Record<string, { x: number; y: number }> = {};
  Object.entries(byDepth).forEach(([dd, ids]) => {
    ids.sort();
    ids.forEach((id, i) => {
      pos[id] = { x: Number(dd) * 260, y: i * 78 - (ids.length * 78) / 2 + 300 };
    });
  });
  return pos;
}

export default function GraphExplorer({
  snapshot,
  degradation,
  hiddenEdgeIds,
  incidentTargets,
  selectedNodeId,
  onSelectNode,
  layerFilter,
}: Props) {
  const positions = useMemo(() => layout(snapshot), [snapshot]);

  const nodes: Node[] = useMemo(() => {
    const capIds = new Set(snapshot.capabilities.map((c) => c.capability_id));
    const all = [
      ...snapshot.capabilities.map((c) => ({
        id: c.capability_id,
        name: c.name,
        type: "capability",
        epistemic: "observed",
      })),
      ...snapshot.nodes.map((n) => ({
        id: n.node_id,
        name: n.name,
        type: n.node_type,
        epistemic: n.epistemic_status,
      })),
    ];
    return all
      .filter((n) => layerFilter[n.epistemic] !== false)
      .map((n) => {
        const deg = degradation[n.id] ?? 0;
        const isCap = capIds.has(n.id);
        const isTarget = incidentTargets.includes(n.id);
        return {
          id: n.id,
          position: positions[n.id] ?? { x: 0, y: 0 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          data: { label: `${n.name}${deg > 0.05 ? ` · ${(deg * 100).toFixed(0)}%` : ""}` },
          style: {
            background: deg > 0.05 ? "color-mix(in srgb, var(--bg-inset) 60%, " + severityColor(deg) + " 40%)" : "var(--bg-inset)",
            color: "var(--text)",
            border: `${selectedNodeId === n.id ? 2.5 : isCap ? 2 : 1.5}px ${n.epistemic === "inferred" ? "dashed" : "solid"} ${
              selectedNodeId === n.id ? "var(--text)" : isTarget ? "var(--red)" : epistemicColor(n.epistemic)
            }`,
            borderRadius: isCap ? 10 : 6,
            fontSize: 11,
            width: 190,
            padding: "6px 8px",
          },
        } as Node;
      });
  }, [snapshot, degradation, incidentTargets, selectedNodeId, positions, layerFilter]);

  const edges: Edge[] = useMemo(
    () =>
      snapshot.edges
        .filter((e) => layerFilter[e.epistemic_status] !== false)
        .map((e) => {
          const hidden = hiddenEdgeIds.includes(e.edge_id);
          const color = hidden ? "var(--gray)" : epistemicColor(e.epistemic_status);
          return {
            id: e.edge_id,
            source: e.from_node,
            target: e.to_node,
            label: hidden ? "hidden" : e.edge_type,
            labelStyle: { fill: "var(--text-dim)", fontSize: 9 },
            labelBgStyle: { fill: "var(--bg-panel)", opacity: 0.85 },
            style: {
              stroke: color,
              strokeWidth: 1 + e.criticality_weight * 1.6,
              strokeDasharray: hidden ? "2 6" : e.epistemic_status === "inferred" ? "6 4" : undefined,
              opacity: hidden ? 0.45 : 0.9,
            },
            markerEnd: { type: MarkerType.ArrowClosed, color },
          } as Edge;
        }),
    [snapshot, hiddenEdgeIds, layerFilter],
  );

  return (
    <div className="h-[540px] w-full" data-testid="graph-explorer">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(_, node) => onSelectNode(node.id)}
        onPaneClick={() => onSelectNode(null)}
        fitView
        minZoom={0.3}
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
      >
        <Background color="#2a2e37" gap={24} />
      </ReactFlow>
    </div>
  );
}
