"use client";

import { useEffect, useState } from "react";
import { api, Json, epistemicColor } from "@/lib/api";
import { Loading, ErrorBox } from "@/components/AsyncState";

export default function EvidencePage() {
  const [data, setData] = useState<Json | null>(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api("/api/evidence").then(setData).catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!data) return <Loading />;

  const evidence = data.evidence.filter(
    (e: Json) => !filter || e.evidence_id.includes(filter) || e.statement.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <div className="space-y-3">
      <div className="panel p-4">
        <h1 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">
          Assumptions ({data.assumptions.length})
        </h1>
        <p className="mb-2 text-xs text-[var(--text-dim)]">
          These are modeling hypotheses, not evidence. Every simulated impact links back to them.
        </p>
        {data.assumptions.map((a: Json) => (
          <div key={a.assumption_id} className="inset mb-1.5 p-2 text-xs">
            <span className="label-inferred">[{a.epistemic_status}]</span>{" "}
            <span className="font-semibold">{a.assumption_id}</span>: {a.statement}
            {a.supports?.length > 0 && (
              <span className="text-[var(--text-dim)]"> · supports {a.supports.join(", ")}</span>
            )}
          </div>
        ))}
      </div>
      <div className="panel p-4">
        <div className="mb-2 flex items-center justify-between">
          <h1 className="text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">
            Evidence registry ({evidence.length})
          </h1>
          <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter…"
            className="inset px-2 py-1 text-xs" />
        </div>
        <div className="max-h-[560px] space-y-1.5 overflow-y-auto">
          {evidence.map((e: Json) => (
            <div key={e.evidence_id} className="inset p-2 text-xs">
              <span style={{ color: epistemicColor(e.epistemic_status) }}>[{e.epistemic_status}]</span>{" "}
              <span className="font-semibold">{e.label}</span>
              <div className="text-[var(--text-dim)]">{e.statement}</div>
              <div className="text-[10px] text-[var(--text-dim)]">
                {e.evidence_id} · locator: {JSON.stringify(e.locator)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
