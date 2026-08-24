"use client";

import { Json, Snapshot, epistemicColor, fmtMin } from "@/lib/api";

interface Props {
  snapshot: Snapshot;
  selectedNodeId: string | null;
  evidenceById: Record<string, Json>;
  degradation: Record<string, number>;
  onClose: () => void;
}

export default function EvidenceDrawer({ snapshot, selectedNodeId, evidenceById, degradation, onClose }: Props) {
  if (!selectedNodeId) return null;
  const node = snapshot.nodes.find((n) => n.node_id === selectedNodeId);
  const cap = snapshot.capabilities.find((c) => c.capability_id === selectedNodeId);
  const name = node?.name ?? cap?.name ?? selectedNodeId;
  const incoming = snapshot.edges.filter((e) => e.to_node === selectedNodeId);
  const outgoing = snapshot.edges.filter((e) => e.from_node === selectedNodeId);
  const evidenceIds = [...(node?.evidence_ids ?? []), ...outgoing.flatMap((e) => e.evidence_ids)];
  const deg = degradation[selectedNodeId] ?? 0;

  return (
    <div className="panel p-3 text-xs" data-testid="evidence-drawer">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold text-[var(--text)]">{name}</h3>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--text)]">✕</button>
      </div>
      {node && (
        <div className="mb-2 grid grid-cols-2 gap-x-2 gap-y-0.5 text-[var(--text-dim)]">
          <span>type: {node.node_type}</span>
          <span>
            epistemic: <span style={{ color: epistemicColor(node.epistemic_status) }}>{node.epistemic_status}</span>
          </span>
          <span>capacity: {node.capacity ? `${node.capacity} ${node.capacity_unit ?? ""}` : "—"}</span>
          <span>recovery: {fmtMin(node.recovery_time_minutes)}</span>
          <span>substitutability: {node.substitutability}</span>
          <span>observability: {node.observability}</span>
          <span className="col-span-2">
            current degradation:{" "}
            <span style={{ color: deg > 0.05 ? "var(--amber)" : "var(--green)" }}>{(deg * 100).toFixed(1)}%</span>{" "}
            <span className="label-simulated">(simulated)</span>
          </span>
        </div>
      )}

      <h4 className="mt-2 font-semibold text-[var(--text-dim)]">Depends on ({outgoing.length})</h4>
      {outgoing.map((e) => (
        <div key={e.edge_id} className="inset mt-1 p-1.5">
          <span style={{ color: epistemicColor(e.epistemic_status) }}>{e.epistemic_status}</span>{" "}
          {e.edge_type} → {e.to_node} · w={e.criticality_weight} · lag {e.propagation_lag_minutes.min}–
          {e.propagation_lag_minutes.max}m · conf {e.confidence}
          {e.substitution_options.length > 0 && (
            <span className="text-[var(--green)]"> · substitutes: {e.substitution_options.join(", ")}</span>
          )}
        </div>
      ))}
      <h4 className="mt-2 font-semibold text-[var(--text-dim)]">Depended on by ({incoming.length})</h4>
      {incoming.map((e) => (
        <div key={e.edge_id} className="inset mt-1 p-1.5">
          {e.from_node} · {e.edge_type} · w={e.criticality_weight}
        </div>
      ))}

      <h4 className="mt-2 font-semibold text-[var(--text-dim)]">Evidence</h4>
      {evidenceIds.length === 0 && <div className="text-[var(--amber)]">No evidence declared — treat as unknown.</div>}
      {evidenceIds.map((id) => {
        const ev = evidenceById[id];
        if (!ev) return <div key={id} className="text-[var(--amber)]">{id}: missing record</div>;
        return (
          <div key={id} className="inset mt-1 p-1.5">
            <span style={{ color: epistemicColor(ev.epistemic_status) }}>[{ev.epistemic_status}]</span>{" "}
            <span className="text-[var(--text)]">{ev.label}</span>
            <div className="text-[var(--text-dim)]">{ev.statement}</div>
          </div>
        );
      })}
    </div>
  );
}
