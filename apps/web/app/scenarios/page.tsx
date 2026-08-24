"use client";

import { useEffect, useState } from "react";
import { api, Json } from "@/lib/api";
import { Loading, ErrorBox } from "@/components/AsyncState";

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Json[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api("/api/scenarios").then(setScenarios).catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!scenarios) return <Loading />;

  return (
    <div className="panel p-4">
      <h1 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">
        Compiled scenarios
      </h1>
      {scenarios.length === 0 && <div className="text-sm text-[var(--text-dim)]">No scenarios compiled yet.</div>}
      {scenarios.map((s) => (
        <div key={s.id} className="inset mb-2 p-2.5 text-xs">
          <div className="font-semibold">{s.id}</div>
          <div className="text-[var(--text-dim)]">
            capability {s.capability_id} · incident {s.incident_id} · seed {s.scenario_json.seed} · horizon{" "}
            {s.scenario_json.horizon_minutes}m
            {s.scenario_json.hidden_edge_ids.length > 0 && (
              <span className="text-[var(--amber)]"> · {s.scenario_json.hidden_edge_ids.length} hidden edge(s)</span>
            )}
          </div>
          <div className="break-all text-[10px] text-[var(--text-dim)]">{s.scenario_hash}</div>
        </div>
      ))}
    </div>
  );
}
