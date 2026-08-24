"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Json } from "@/lib/api";
import { vget, vpost } from "@/lib/verine";
import { Loading, ErrorBox } from "@/components/AsyncState";

export default function WatchPacksPage() {
  const [packs, setPacks] = useState<Json[] | null>(null);
  const [connectors, setConnectors] = useState<Json[]>([]);
  const [status, setStatus] = useState<Record<string, Json>>({});
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    Promise.all([vget<Json[]>("/watch-packs"), vget<Json[]>("/connectors")])
      .then(async ([p, c]) => {
        setPacks(p);
        setConnectors(c);
        const st: Record<string, Json> = {};
        for (const pack of p) st[pack.watch_pack_id] = await vget(`/watch-packs/${pack.watch_pack_id}/status`);
        setStatus(st);
      })
      .catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  const poll = async (id: string) => {
    await vpost(`/watch-packs/${id}/poll`);
    load();
  };

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!packs) return <Loading />;

  return (
    <div className="space-y-3">
      <div className="panel p-4">
        <h1 className="text-lg font-bold">Watch Packs</h1>
        <p className="mt-1 text-sm text-[var(--text-dim)]">
          A watch pack binds one critical capability to read-only connectors, entity aliases, and
          geography mappings. Live mode is disabled by default; these packs run against offline fixtures
          until a connector is explicitly enabled for live polling.
        </p>
      </div>

      {packs.map((p) => (
        <div key={p.watch_pack_id} className="panel p-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-semibold">{p.name}</span>
              <span className="ml-2 text-xs text-[var(--text-dim)]">{p.capability_id}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="badge" style={{ color: p.status === "running" ? "var(--green)" : "var(--text-dim)" }}>
                {p.status}
              </span>
              <button onClick={() => poll(p.watch_pack_id)}
                className="rounded border border-[var(--border)] bg-[var(--bg-inset)] px-3 py-1 text-xs hover:border-[var(--amber)]">
                One-shot poll
              </button>
              <Link href="/live" className="rounded bg-[var(--amber)] px-3 py-1 text-xs font-semibold text-black">
                Open war room →
              </Link>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
            {(status[p.watch_pack_id]?.connectors ?? []).map((c: Json) => (
              <div key={c.connector_id} className="inset p-2">
                <div className="flex justify-between">
                  <span className="text-[var(--text)]">{c.connector_type}</span>
                  <span style={{ color: c.fixture_mode ? "var(--violet)" : "var(--green)" }}>
                    {c.fixture_mode ? "fixture" : "live"}
                  </span>
                </div>
                <div className="text-[10px] text-[var(--text-dim)]">
                  {c.enabled ? "enabled" : "disabled"} · seen {c.seen_events} · polled {c.last_polled_at?.slice(11, 19) ?? "never"}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="panel p-4">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">
          Connectors ({connectors.length})
        </h2>
        {connectors.map((c) => (
          <div key={c.connector_id} className="inset mb-1.5 flex items-center justify-between p-2 text-xs">
            <span><span className="text-[var(--text)]">{c.connector_type}</span> · {c.label}</span>
            <span className="text-[var(--text-dim)]">
              {c.fixture_path ? "offline fixture" : "live"} · strength {c.source_strength} · group {c.source_independence_group}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
