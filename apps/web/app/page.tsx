"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Capability, Incident, Json } from "@/lib/api";
import { Loading, ErrorBox } from "@/components/AsyncState";

export default function Launcher() {
  const [caps, setCaps] = useState<Capability[] | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [meta, setMeta] = useState<Json>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    Promise.all([api("/api/capabilities"), api("/api/incidents"), api("/api/presets")])
      .then(([c, i, m]) => {
        setCaps(c);
        setIncidents(i);
        setMeta(m);
      })
      .catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!caps) return <Loading />;

  return (
    <div className="space-y-4">
      <div className="panel p-5">
        <h1 className="text-lg font-bold">Capability-level crisis compiler</h1>
        <p className="mt-1 max-w-3xl text-sm text-[var(--text-dim)]">
          Load a critical business capability, inject a compound incident, watch the failure propagate through
          the dependency graph, compare containment strategies under constraints, inspect what is observed
          versus inferred versus simulated, and export a reproducible Resilience Case File.
        </p>
        <p className="mt-2 text-xs text-[var(--violet)]">
          Synthetic war room: every result is a simulation over a fixture graph — never a prediction about a
          real organization.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="panel p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">Capabilities</h2>
          {caps.map((c) => (
            <div key={c.capability_id} className="inset mb-2 p-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold">{c.name}</span>
                <span className="badge text-[var(--red)]">{c.criticality}</span>
              </div>
              <div className="mt-1 text-xs text-[var(--text-dim)]">
                {c.description} · target {(c.target_service_level * 100).toFixed(1)}% · floor{" "}
                {(c.minimum_service_level * 100).toFixed(0)}% · {c.unit}
              </div>
              <Link href="/war-room" data-testid="open-war-room"
                className="mt-2 inline-block rounded bg-[var(--amber)] px-3 py-1 text-xs font-semibold text-black hover:opacity-90">
                Open war room →
              </Link>
            </div>
          ))}
        </div>
        <div className="panel p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">
            Incident library <span className="label-simulated normal-case">(synthetic)</span>
          </h2>
          {incidents.map((i) => (
            <div key={i.incident_id} className="inset mb-2 p-2.5 text-xs">
              <div className="flex justify-between">
                <span className="font-semibold text-[var(--text)]">{i.name}</span>
                <span className={i.incident_type === "compound" ? "text-[var(--red)]" : "text-[var(--amber)]"}>
                  {i.incident_type}
                </span>
              </div>
              <div className="mt-0.5 text-[var(--text-dim)]">
                {i.components.length} component(s) · severity {i.severity} · {i.duration_minutes}m
              </div>
            </div>
          ))}
          {meta && (
            <div className="mt-3 text-[11px] text-[var(--text-dim)]">
              Fixture: {meta.fixture_id} · seed {meta.default_seed} ·{" "}
              {meta.graph_warnings.length} graph warning(s)
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
