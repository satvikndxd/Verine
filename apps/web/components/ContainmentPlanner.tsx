"use client";

import { useState } from "react";
import { api, Constraints, Json, fmtMin } from "@/lib/api";

interface Props {
  scenarioId: string;
  initial: Json; // containment result from the run
  constraints: Constraints;
}

function SetCard({ s, title, tone }: { s: Json; title: string; tone: string }) {
  return (
    <div className="inset p-2.5 text-xs">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-semibold" style={{ color: tone }}>{title}</span>
        <span className="badge label-simulated">simulated</span>
      </div>
      <div className="mb-1 text-[var(--text)]">
        {s.action_ids.length ? s.action_ids.join(" + ") : "No action"}
      </div>
      <div className="grid grid-cols-2 gap-x-3 text-[var(--text-dim)]">
        <span>loss: {s.expected_service_loss_sl_hours} sl·h</span>
        <span>cost: ${Number(s.total_cost ?? 0).toLocaleString()}</span>
        <span>floor breach: {s.floor_breach_duration_minutes ?? 0}m</span>
        <span>effect after: {fmtMin(s.time_to_effect_minutes ?? 0)}</span>
        <span>collateral ≤ {s.max_collateral_risk}</span>
        <span>reversibility: {s.mean_reversibility}</span>
      </div>
    </div>
  );
}

export default function ContainmentPlanner({ scenarioId, initial, constraints }: Props) {
  const [result, setResult] = useState<Json>(initial);
  const [budget, setBudget] = useState(constraints.budget);
  const [deadline, setDeadline] = useState(constraints.deadline_minutes);
  const [collateral, setCollateral] = useState(constraints.max_collateral_risk);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRejected, setShowRejected] = useState(false);

  const recompute = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api("/api/containment/optimize", {
        method: "POST",
        body: JSON.stringify({
          scenario_id: scenarioId,
          constraints_override: {
            ...constraints,
            budget,
            deadline_minutes: deadline,
            max_collateral_risk: collateral,
          },
        }),
      });
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel p-3" data-testid="containment-planner">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)]">
        Containment planner
      </h3>
      <div className="mb-3 grid grid-cols-3 gap-3 text-xs">
        <label>
          Budget: <span className="text-[var(--text)]">${budget.toLocaleString()}</span>
          <input type="range" min={1000} max={200000} step={1000} value={budget}
            onChange={(e) => setBudget(Number(e.target.value))} className="w-full" data-testid="budget-slider" />
        </label>
        <label>
          Deadline: <span className="text-[var(--text)]">{fmtMin(deadline)}</span>
          <input type="range" min={15} max={360} step={15} value={deadline}
            onChange={(e) => setDeadline(Number(e.target.value))} className="w-full" />
        </label>
        <label>
          Max collateral: <span className="text-[var(--text)]">{collateral.toFixed(2)}</span>
          <input type="range" min={0} max={1} step={0.05} value={collateral}
            onChange={(e) => setCollateral(Number(e.target.value))} className="w-full" />
        </label>
      </div>
      <button onClick={recompute} disabled={busy} data-testid="recompute-containment"
        className="mb-3 rounded border border-[var(--border)] bg-[var(--bg-inset)] px-3 py-1 text-xs hover:border-[var(--amber)] disabled:opacity-50">
        {busy ? "Recomputing…" : "Recompute feasible sets"}
      </button>
      {error && <div className="mb-2 text-xs text-[var(--red)]">{error}</div>}

      <div className="space-y-2">
        <SetCard s={result.baseline_no_action} title="No action (baseline)" tone="var(--gray)" />
        {result.chosen_set ? (
          <SetCard s={result.chosen_set} title="Chosen set" tone="var(--green)" />
        ) : (
          <div className="inset p-2.5 text-xs text-[var(--amber)]">
            No feasible action set improves on doing nothing under these constraints. See evidence requests.
          </div>
        )}
        {result.runner_up_sets?.map((s: Json, i: number) => (
          <SetCard key={i} s={s} title={`Runner-up ${i + 1}`} tone="var(--text-dim)" />
        ))}
      </div>

      <button onClick={() => setShowRejected(!showRejected)} className="mt-2 text-xs text-[var(--text-dim)] underline">
        {showRejected ? "Hide" : "Show"} rejected sets ({result.rejected_count})
      </button>
      {showRejected && (
        <div className="mt-2 max-h-48 space-y-1 overflow-y-auto text-[11px]">
          {result.rejected_sets.map((r: Json, i: number) => (
            <div key={i} className="inset p-2">
              <div className="text-[var(--text)]">{r.action_ids.join(" + ")}</div>
              {r.reasons.map((reason: string, j: number) => (
                <div key={j} className="text-[var(--red)]">✕ {reason}</div>
              ))}
            </div>
          ))}
        </div>
      )}
      <div className="mt-2 text-[10px] text-[var(--text-dim)]">
        Utility weights (user-visible, no hidden optimum): {JSON.stringify(result.weights)}. {result.disclaimer}
      </div>
    </div>
  );
}
