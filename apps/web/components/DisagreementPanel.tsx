"use client";

import { Json } from "@/lib/api";

export default function DisagreementPanel({ report, comparables }: { report: Json; comparables: Json[] }) {
  const levelColor =
    report.overall_level === "material" ? "var(--red)" : report.overall_level === "moderate" ? "var(--amber)" : "var(--green)";
  return (
    <div className="panel p-3" data-testid="disagreement-panel">
      <div className="mb-2 flex items-center gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)]">Model disagreement</h3>
        <span className="badge" style={{ color: levelColor, borderColor: levelColor }}>
          {report.overall_level}
        </span>
      </div>
      <p className="mb-3 text-[11px] text-[var(--text-dim)]">{report.interpretation}</p>

      <table className="mb-3 w-full text-[11px]">
        <thead>
          <tr className="text-left text-[var(--text-dim)]">
            <th className="pr-2">model</th>
            <th className="pr-2">max degradation</th>
            <th className="pr-2">time to floor</th>
            <th className="pr-2">recovery</th>
            <th>affected nodes</th>
          </tr>
        </thead>
        <tbody>
          {comparables.map((c) => (
            <tr key={c.model_id} className="border-t border-[var(--border)]">
              <td className="py-1 pr-2 label-simulated">{c.model_id}</td>
              <td className="pr-2">{c.max_degradation ?? "—"}</td>
              <td className="pr-2">{c.time_to_floor_minutes ?? "—"}</td>
              <td className="pr-2">{c.recovery_time_minutes ?? "—"}</td>
              <td>{c.affected_nodes?.length ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {report.areas.map((a: Json) => (
        <div key={a.metric} className="inset mb-2 p-2 text-[11px]">
          <div className="mb-1 flex justify-between">
            <span className="font-semibold text-[var(--text)]">{a.metric}</span>
            <span style={{ color: a.normalized_disagreement > 0.25 ? "var(--red)" : "var(--amber)" }}>
              disagreement {(a.normalized_disagreement * 100).toFixed(0)}%
            </span>
          </div>
          <div className="text-[var(--text-dim)]">
            <div>likely reasons: {a.likely_reasons.join("; ")}</div>
            <div>missing evidence: {a.missing_evidence.join("; ")}</div>
            <div className="text-[var(--blue)]">→ {a.recommended_next_step}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
