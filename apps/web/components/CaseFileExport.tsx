"use client";

import { useState } from "react";
import { Json, api } from "@/lib/api";

function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function caseToMarkdown(c: Json): string {
  const lines = [
    `# Resilience Case File ${c.case_file_id}`,
    ``,
    `> ${c.disclaimer}`,
    ``,
    `| Field | Value |`,
    `| --- | --- |`,
    `| Case type | ${c.case_type} |`,
    `| Scenario | ${c.scenario_id} |`,
    `| Capability status | ${c.capability_status} |`,
    `| Executed at | ${c.executed_at} |`,
    `| Seed | ${c.seed} |`,
    `| Models | ${c.model_versions.join(", ")} |`,
    `| Graph hash | \`${c.graph_hash}\` |`,
    `| Scenario hash | \`${c.scenario_hash}\` |`,
    `| Run hash | \`${c.run_hash}\` |`,
    ``,
    `## Blast radius`,
    `${c.blast_radius.affected_node_count} nodes affected: ${c.blast_radius.affected_nodes.join(", ")}`,
    ``,
    `## Top pathways`,
    ...c.top_pathways.map((p: Json) => `- ${p.description} (strength ${p.strength}, first impact ${p.first_impact_minutes}m)`),
    ``,
    `## Containment sets (simulated)`,
    ...c.containment_sets.map(
      (s: Json) =>
        `- ${s.action_ids.join(" + ") || "no action"}: loss ${s.expected_service_loss_sl_hours} sl·h, cost $${s.total_cost}, floor breach ${s.floor_breach_duration_minutes}m`,
    ),
    ``,
    `## Model disagreement (${c.model_disagreement.overall_level})`,
    ...c.model_disagreement.areas.map(
      (a: Json) => `- ${a.metric}: ${(a.normalized_disagreement * 100).toFixed(0)}% — ${a.likely_reasons.join("; ")}`,
    ),
    ``,
    `## Evidence requests`,
    ...c.evidence_requests.map((r: Json) => `- ${r.request} (~$${r.estimated_cost_usd}, ~${r.estimated_time_minutes}m)`),
    ``,
    `## Unknowns`,
    ...c.unknowns.map((u: Json) => `- [${u.kind}] ${u.detail}`),
    ``,
    `## Assumptions`,
    ...c.assumptions.map((a: Json) => `- ${a.assumption_id}: ${a.statement}`),
    ``,
    `Replay: \`${c.replay_command}\``,
  ];
  return lines.join("\n");
}

export default function CaseFileExport({ caseFile }: { caseFile: Json }) {
  const [verdict, setVerdict] = useState<Json | null>(null);
  const [busy, setBusy] = useState(false);

  const verify = async () => {
    setBusy(true);
    try {
      setVerdict(await api(`/api/cases/${caseFile.case_file_id}/replay`, { method: "POST" }));
    } catch (e) {
      setVerdict({ error: String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel p-3 text-xs" data-testid="case-export">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)]">
        Resilience Case File
      </h3>
      <div className="mb-2 grid grid-cols-1 gap-0.5 text-[var(--text-dim)]">
        <span>id: <span className="text-[var(--text)]">{caseFile.case_file_id}</span></span>
        <span>status: <span className="text-[var(--amber)]">{caseFile.capability_status}</span></span>
        <span className="break-all">run hash: {caseFile.run_hash}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => download(`${caseFile.case_file_id}.json`, JSON.stringify(caseFile, null, 2), "application/json")}
          className="rounded border border-[var(--border)] bg-[var(--bg-inset)] px-3 py-1 hover:border-[var(--blue)]"
          data-testid="export-json"
        >
          Export JSON
        </button>
        <button
          onClick={() => download(`${caseFile.case_file_id}.md`, caseToMarkdown(caseFile), "text/markdown")}
          className="rounded border border-[var(--border)] bg-[var(--bg-inset)] px-3 py-1 hover:border-[var(--blue)]"
          data-testid="export-md"
        >
          Export Markdown
        </button>
        <button
          onClick={verify}
          disabled={busy}
          className="rounded border border-[var(--border)] bg-[var(--bg-inset)] px-3 py-1 hover:border-[var(--violet)] disabled:opacity-50"
          data-testid="verify-replay"
        >
          {busy ? "Replaying…" : "Verify replay"}
        </button>
      </div>
      {verdict && (
        <div className="mt-2 inset p-2" data-testid="replay-verdict">
          {verdict.error ? (
            <span className="text-[var(--red)]">{verdict.error}</span>
          ) : verdict.hashes_match ? (
            <span className="text-[var(--green)]">✓ Replay hash matches: {verdict.actual_run_hash?.slice(0, 24)}…</span>
          ) : (
            <span className="text-[var(--red)]">✕ Hash mismatch — run is not reproducible. {verdict.reason ?? ""}</span>
          )}
        </div>
      )}
    </div>
  );
}
