"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, Json } from "@/lib/api";
import { Loading, ErrorBox } from "@/components/AsyncState";
import CaseFileExport from "@/components/CaseFileExport";

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<Json | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api(`/api/cases/${id}`).then(setDoc).catch((e) => setError(String(e)));
  };
  useEffect(load, [id]);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!doc) return <Loading />;
  const c = doc.case_json;

  return (
    <div className="space-y-3">
      <CaseFileExport caseFile={c} />
      <div className="panel p-4 text-xs">
        <h2 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">Lineage</h2>
        <div className="grid grid-cols-1 gap-1 text-[var(--text-dim)]">
          <span>scenario: {c.scenario_id}</span>
          <span className="break-all">graph hash: {c.graph_hash}</span>
          <span className="break-all">scenario hash: {c.scenario_hash}</span>
          <span className="break-all">run hash: {c.run_hash}</span>
          <span>models: {c.model_versions.join(", ")} · seed {c.seed}</span>
          <span>replay: <code className="text-[var(--blue)]">{c.replay_command}</code></span>
        </div>
      </div>
      <div className="panel p-4 text-xs">
        <h2 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">Full case JSON</h2>
        <pre className="max-h-[480px] overflow-auto text-[10px] text-[var(--text-dim)]">
          {JSON.stringify(c, null, 2)}
        </pre>
      </div>
    </div>
  );
}
