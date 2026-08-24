"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Json } from "@/lib/api";
import { Loading, ErrorBox } from "@/components/AsyncState";

export default function CasesPage() {
  const [cases, setCases] = useState<Json[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api("/api/cases").then(setCases).catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!cases) return <Loading />;

  return (
    <div className="panel p-4">
      <h1 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--text-dim)]">
        Resilience Case Files
      </h1>
      {cases.length === 0 && (
        <div className="text-sm text-[var(--text-dim)]">
          No case files yet. Run a scenario in the <Link className="text-[var(--amber)]" href="/war-room">war room</Link>.
        </div>
      )}
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-[var(--text-dim)]">
            <th className="pb-1 pr-3">case</th>
            <th className="pr-3">status</th>
            <th className="pr-3">executed</th>
            <th>run hash</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.case_file_id} className="border-t border-[var(--border)]">
              <td className="py-1.5 pr-3">
                <Link href={`/cases/${c.case_file_id}`} className="text-[var(--blue)] hover:underline">
                  {c.case_file_id}
                </Link>
              </td>
              <td className="pr-3 text-[var(--amber)]">{c.capability_status}</td>
              <td className="pr-3 text-[var(--text-dim)]">{c.executed_at}</td>
              <td className="break-all text-[var(--text-dim)]">{c.run_hash?.slice(0, 30)}…</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
