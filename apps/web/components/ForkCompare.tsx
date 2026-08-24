"use client";

import { useState } from "react";
import { Json, fmtMin } from "@/lib/api";
import { vpost } from "@/lib/verine";

const ACTIONS = [
  { id: "act_failover_backup_processor", label: "Failover to backup processor" },
  { id: "act_shift_traffic_secondary_region", label: "Shift traffic to secondary region" },
  { id: "act_enable_fraud_fallback_rules", label: "Enable fraud fallback rules" },
  { id: "act_queue_backpressure", label: "Queue backpressure" },
];

export default function ForkCompare({ caseId, watchPackId }: { caseId: string; watchPackId: string }) {
  const [forks, setForks] = useState<Json[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runFork = async (action_ids: string[], label: string) => {
    setBusy(true);
    setError(null);
    try {
      const fork = await vpost(`/cases/${caseId}/fork`, { action_ids, watch_pack_id: watchPackId });
      setForks((prev) => [...prev.filter((f) => f.label !== label), { ...fork, label }]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel p-3 text-xs" data-testid="fork-compare">
      <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
        Containment forks <span className="label-simulated normal-case">(simulated, reversible only)</span>
      </h3>
      <div className="mb-2 flex flex-wrap gap-1">
        <button onClick={() => runFork([], "No action")} disabled={busy}
          className="rounded border border-[var(--border)] px-2 py-1 hover:border-[var(--gray)]" data-testid="fork-no-action">
          No action
        </button>
        {ACTIONS.map((a) => (
          <button key={a.id} onClick={() => runFork([a.id], a.label)} disabled={busy}
            className="rounded border border-[var(--border)] px-2 py-1 hover:border-[var(--amber)]">
            {a.label}
          </button>
        ))}
      </div>
      {error && <div className="mb-2 text-[var(--red)]">{error}</div>}
      {busy && <div className="mb-2 text-[var(--text-dim)]">Simulating fork…</div>}

      <div className="space-y-1.5">
        {forks.map((f) => (
          <div key={f.fork_id} className="inset p-2" data-testid="fork-result">
            <div className="flex justify-between">
              <span className="font-semibold text-[var(--text)]">{f.label}</span>
              <span className="badge" style={{ color: f.status === "simulated" ? "var(--violet)" : "var(--red)" }}>
                {f.status}
              </span>
            </div>
            {f.status === "simulated" ? (
              <div className="grid grid-cols-2 gap-x-3 text-[var(--text-dim)]">
                <span>min SL: {(f.metrics.min_service_level * 100).toFixed(1)}%</span>
                <span>floor breach: {fmtMin(f.metrics.floor_breach_duration_minutes)}</span>
                <span>loss: {f.metrics.expected_service_loss_sl_hours} sl·h</span>
                <span>cost: ${Number(f.metrics.total_cost).toLocaleString()}</span>
              </div>
            ) : (
              <ul className="list-disc pl-4 text-[var(--red)]">
                {(f.feasibility_reasons ?? []).map((r: string, i: number) => <li key={i}>{r}</li>)}
              </ul>
            )}
            {f.run_hash && <div className="mt-1 text-[10px] text-[var(--text-dim)]">run {f.run_hash.slice(0, 22)}…</div>}
          </div>
        ))}
        {!forks.length && !busy && (
          <div className="text-[var(--text-dim)]">Compare no-action against a reversible containment path.</div>
        )}
      </div>
    </div>
  );
}
