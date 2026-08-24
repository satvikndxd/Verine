"use client";

import { useEffect, useState } from "react";
import { api, Json } from "@/lib/api";
import { Loading, ErrorBox } from "@/components/AsyncState";

const statusColor = (s: string) =>
  s === "pass" ? "var(--green)" : s === "fail" ? "var(--red)" : "var(--amber)";

export default function ExperimentsPage() {
  const [data, setData] = useState<Json | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api("/api/experiments").then(setData).catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!data) return <Loading />;

  return (
    <div className="space-y-3">
      {Object.entries(data.benchmarks as Record<string, Json>).map(([name, bench]) => (
        <div key={name} className="panel p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">{name}</h2>
          {bench.note && <p className="mb-2 text-xs text-[var(--violet)]">{bench.note}</p>}
          {bench.tasks?.map((t: Json) => (
            <div key={t.task_id} className="inset mb-1.5 flex items-start gap-3 p-2 text-xs">
              <span className="w-8 font-bold">{t.task_id}</span>
              <span className="w-16 font-semibold" style={{ color: statusColor(t.status) }}>{t.status}</span>
              <div>
                <div>{t.name}</div>
                <div className="text-[var(--text-dim)]">baseline: {t.baseline}</div>
              </div>
            </div>
          ))}
        </div>
      ))}
      <div className="panel p-4">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">
          Experiment registry
        </h2>
        {(data.registry.experiments ?? []).map((e: Json) => (
          <div key={e.experiment_id} className="inset mb-1.5 p-2 text-xs">
            <span className="font-semibold">{e.experiment_id}</span> — {e.question}
            <span className="ml-2" style={{ color: statusColor(e.result === "pending" ? "pending" : "pass") }}>
              [{e.result}]
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
