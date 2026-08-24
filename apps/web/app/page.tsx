"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Json } from "@/lib/api";
import { vget } from "@/lib/verine";
import { Loading, ErrorBox } from "@/components/AsyncState";

export default function Launcher() {
  const [packs, setPacks] = useState<Json[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    vget<Json[]>("/watch-packs").then(setPacks).catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!packs) return <Loading />;

  return (
    <div className="space-y-4">
      <div className="panel p-6">
        <h1 className="text-xl font-bold">Before the failure becomes obvious, see the chain.</h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--text-dim)]">
          VERINE converts external signals and internal evidence into a living capability graph, detects
          possible compound incidents, shows what may break next and when, exposes hidden dependencies and
          uncertainty, compares reversible containment paths, and preserves every decision as a replayable
          Resilience Case File.
        </p>
        <p className="mt-2 max-w-3xl text-xs text-[var(--violet)]">
          Offline by default. External signals are evidence, never confirmed internal impact. Model
          projections carry intervals and assumptions — never &quot;will fail at T.&quot; Live connectors are
          disabled until explicitly enabled.
        </p>
        <div className="mt-4 flex gap-2">
          <Link href="/live" className="rounded bg-[var(--amber)] px-4 py-2 text-sm font-semibold text-black hover:opacity-90" data-testid="open-live">
            Open Live War Room →
          </Link>
          <Link href="/providers" className="rounded border border-[var(--border)] px-4 py-2 text-sm hover:border-[var(--blue)]">
            Configure AI Providers
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="panel p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">Watch packs</h2>
          {packs.map((p) => (
            <div key={p.watch_pack_id} className="inset mb-2 p-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold">{p.name}</span>
                <span className="badge text-[var(--red)]">critical capability</span>
              </div>
              <div className="mt-1 text-xs text-[var(--text-dim)]">
                {p.capability_id} · {p.connector_ids.length} connector(s)
              </div>
              <Link href="/live" className="mt-2 inline-block rounded bg-[var(--amber)] px-3 py-1 text-xs font-semibold text-black">
                Open war room →
              </Link>
            </div>
          ))}
        </div>
        <div className="panel p-4 text-sm">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">The chain</h2>
          <ol className="space-y-1 text-xs text-[var(--text-dim)]">
            {["Signal arrives (event tape)", "Evidence preserved (raw hash + locator)",
              "Quorum changes (independent corroboration)", "Shadowgraph reveals hidden dependency",
              "Cascade clock projects floor breach interval", "Models disagree (kept, not averaged)",
              "Fork no-action vs reversible containment", "Cited LLM explanation (optional)",
              "Evidence requests for the top unknown", "Case file exported & replayed by hash"].map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-[var(--amber)]">{i + 1}.</span> {s}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
