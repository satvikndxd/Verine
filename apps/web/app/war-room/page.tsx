"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api, Capability, Constraints, Incident, Json, Snapshot, StepState, fmtMin, fmtPct,
} from "@/lib/api";
import { Loading, ErrorBox } from "@/components/AsyncState";
import GraphExplorer from "@/components/GraphExplorer";
import Timeline from "@/components/Timeline";
import ContainmentPlanner from "@/components/ContainmentPlanner";
import DisagreementPanel from "@/components/DisagreementPanel";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import CaseFileExport from "@/components/CaseFileExport";

const EPISTEMIC_LAYERS = ["observed", "inferred", "simulated", "unknown"];

export default function WarRoom() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [meta, setMeta] = useState<Json>(null);
  const [evidenceById, setEvidenceById] = useState<Record<string, Json>>({});
  const [loadError, setLoadError] = useState<string | null>(null);

  const [incidentId, setIncidentId] = useState("inc_compound_payment_crisis");
  const [topology, setTopology] = useState<"known" | "incomplete">("known");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [run, setRun] = useState<Json | null>(null);
  const [scenario, setScenario] = useState<Json | null>(null);
  const [timeIndex, setTimeIndex] = useState(0);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [tab, setTab] = useState<"pathways" | "disagreement" | "unknowns" | "case">("pathways");
  const [layers, setLayers] = useState<Record<string, boolean>>(
    Object.fromEntries(EPISTEMIC_LAYERS.map((l) => [l, true])),
  );

  const load = useCallback(async () => {
    try {
      const m = await api("/api/presets");
      const [snap, incs, ev] = await Promise.all([
        api(`/api/graph/snapshots/${m.graph_snapshot_id}`),
        api("/api/incidents"),
        api("/api/evidence"),
      ]);
      setMeta(m);
      setSnapshot(snap.graph_json);
      setIncidents(incs);
      const byId: Record<string, Json> = {};
      ev.evidence.forEach((e: Json) => (byId[e.evidence_id] = e));
      setEvidenceById(byId);
    } catch (e) {
      setLoadError(String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const hiddenEdges = useMemo(() => {
    if (!meta || topology === "known") return [];
    const preset = meta.scenario_presets.find((p: Json) => p.preset_id === "preset_incomplete_topology_compound");
    return preset?.hidden_edge_ids ?? [];
  }, [meta, topology]);

  const capability: Capability | undefined = snapshot?.capabilities[0];
  const constraints: Constraints | null = meta?.default_constraints ?? null;

  const launch = async () => {
    if (!capability) return;
    setRunning(true);
    setRunError(null);
    try {
      const compiled = await api("/api/scenarios/compile", {
        method: "POST",
        body: JSON.stringify({
          capability_id: capability.capability_id,
          incident_id: incidentId,
          hidden_edge_ids: hiddenEdges,
        }),
      });
      setScenario(compiled);
      const result = await api("/api/simulations/run", {
        method: "POST",
        body: JSON.stringify({ scenario_id: compiled.scenario.scenario_id }),
      });
      setRun(result);
      setTimeIndex(0);
      setTab("pathways");
    } catch (e) {
      setRunError(String(e));
    } finally {
      setRunning(false);
    }
  };

  if (loadError) return <ErrorBox error={loadError} retry={load} />;
  if (!snapshot || !capability || !constraints) return <Loading label="Loading capability graph…" />;

  const det = run?.model_outputs?.deterministic_propagation_v1;
  const steps: StepState[] = det?.steps ?? [];
  const currentStep = steps[Math.min(timeIndex, steps.length - 1)];
  const degradation = currentStep?.node_degradation ?? {};
  const capMetrics = det?.metrics?.capabilities?.[capability.capability_id];
  const incident = incidents.find((i) => i.incident_id === incidentId);
  const incidentTargets = incident?.components.map((c) => c.target_node_id) ?? [];
  const caseFile = run?.case_file;
  const currentSl = currentStep?.service_levels?.[capability.capability_id];

  return (
    <div className="space-y-3">
      {/* Header bar */}
      <div className="panel flex flex-wrap items-center gap-3 px-4 py-2 text-sm">
        <span className="font-semibold">{capability.name}</span>
        <span className="badge text-[var(--blue)]">{capability.criticality}</span>
        {caseFile && (
          <>
            <span className="text-[var(--text-dim)]">RUN: {caseFile.case_file_id}</span>
            <span className="badge text-[var(--green)]">REPLAYABLE</span>
            <span className="badge" style={{
              color: capMetrics?.breached_floor ? "var(--red)" : "var(--amber)",
              borderColor: capMetrics?.breached_floor ? "var(--red)" : "var(--amber)",
            }} data-testid="capability-status">
              {caseFile.capability_status}
            </span>
          </>
        )}
        <div className="ml-auto flex items-center gap-2 text-xs">
          <select value={incidentId} onChange={(e) => setIncidentId(e.target.value)}
            className="inset px-2 py-1" data-testid="incident-select">
            {incidents.map((i) => (
              <option key={i.incident_id} value={i.incident_id}>
                {i.name} {i.incident_type === "compound" ? "· compound" : ""}
              </option>
            ))}
          </select>
          <select value={topology} onChange={(e) => setTopology(e.target.value as "known" | "incomplete")}
            className="inset px-2 py-1" data-testid="topology-select">
            <option value="known">Known topology</option>
            <option value="incomplete">Incomplete topology</option>
          </select>
          <button onClick={launch} disabled={running} data-testid="launch-button"
            className="rounded bg-[var(--amber)] px-4 py-1.5 font-semibold text-black hover:opacity-90 disabled:opacity-50">
            {running ? "Simulating…" : run ? "Re-run scenario" : "Inject incident"}
          </button>
        </div>
      </div>
      {runError && <ErrorBox error={runError} retry={launch} />}

      <div className="grid grid-cols-12 gap-3">
        {/* Left: capability status */}
        <div className="col-span-2 space-y-3">
          <div className="panel p-3 text-xs" data-testid="status-pane">
            <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">Capability status</h3>
            <div className="space-y-1.5">
              <div>
                <div className="text-[var(--text-dim)]">Service level (t)</div>
                <div className="text-xl font-bold" style={{
                  color: currentSl !== undefined && currentSl < capability.minimum_service_level ? "var(--red)" : "var(--text)",
                }}>
                  {run ? fmtPct(currentSl) : fmtPct(capability.target_service_level)}
                </div>
                <div className="text-[10px] text-[var(--text-dim)]">
                  target {fmtPct(capability.target_service_level)} · floor {fmtPct(capability.minimum_service_level)}
                </div>
              </div>
              {capMetrics && (
                <>
                  <div>
                    <div className="text-[var(--text-dim)]">Time to floor</div>
                    <div className="font-semibold" style={{ color: capMetrics.breached_floor ? "var(--red)" : "var(--green)" }}>
                      {capMetrics.breached_floor ? fmtMin(capMetrics.time_to_floor_minutes) : "not breached"}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--text-dim)]">Floor breach duration</div>
                    <div className="font-semibold">{fmtMin(capMetrics.floor_breach_duration_minutes)}</div>
                  </div>
                  <div>
                    <div className="text-[var(--text-dim)]">Recovery (deterministic)</div>
                    <div className="font-semibold">{fmtMin(capMetrics.recovery_time_minutes)}</div>
                  </div>
                  <div>
                    <div className="text-[var(--text-dim)]">Recovery (MC p10–p90)</div>
                    <div className="font-semibold label-simulated">
                      {fmtMin(run.model_outputs.monte_carlo_v1?.aggregates?.recovery_time_minutes?.p10)}–
                      {fmtMin(run.model_outputs.monte_carlo_v1?.aggregates?.recovery_time_minutes?.p90)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--text-dim)]">Blast radius</div>
                    <div className="font-semibold">{det.metrics.affected_node_count} nodes</div>
                  </div>
                  <div>
                    <div className="text-[var(--text-dim)]">Reliability</div>
                    <div className="font-semibold text-[var(--amber)]">{run.unknowns.reliability_label}</div>
                  </div>
                </>
              )}
              {!run && <div className="text-[var(--text-dim)]">Inject an incident to begin.</div>}
            </div>
          </div>

          <div className="panel p-3 text-xs">
            <h3 className="mb-1 font-semibold uppercase tracking-wider text-[var(--text-dim)]">Layers</h3>
            {EPISTEMIC_LAYERS.map((l) => (
              <label key={l} className="flex items-center gap-1.5">
                <input type="checkbox" checked={layers[l]}
                  onChange={(e) => setLayers({ ...layers, [l]: e.target.checked })} />
                <span className={`label-${l === "unknown" ? "unknown" : l}`}>{l}</span>
              </label>
            ))}
            <div className="mt-2 text-[10px] text-[var(--text-dim)]">
              Edge styles: solid blue = observed, dashed amber = inferred (NOT confirmed), violet = simulated,
              faint gray = hidden from models.
            </div>
          </div>
        </div>

        {/* Center: graph + timeline */}
        <div className="col-span-7 space-y-3">
          <div className="panel overflow-hidden">
            <GraphExplorer
              snapshot={snapshot}
              degradation={degradation}
              hiddenEdgeIds={hiddenEdges}
              incidentTargets={run ? incidentTargets : []}
              selectedNodeId={selectedNode}
              onSelectNode={setSelectedNode}
              layerFilter={layers}
            />
          </div>
          {run && steps.length > 0 && (
            <Timeline
              steps={steps}
              capabilityId={capability.capability_id}
              targetSl={capability.target_service_level}
              floorSl={capability.minimum_service_level}
              currentIndex={Math.min(timeIndex, steps.length - 1)}
              onScrub={setTimeIndex}
            />
          )}
        </div>

        {/* Right: decision pane */}
        <div className="col-span-3 space-y-3">
          {selectedNode && (
            <EvidenceDrawer
              snapshot={snapshot}
              selectedNodeId={selectedNode}
              evidenceById={evidenceById}
              degradation={degradation}
              onClose={() => setSelectedNode(null)}
            />
          )}
          {run && scenario && (
            <ContainmentPlanner
              scenarioId={scenario.scenario.scenario_id}
              initial={run.containment}
              constraints={constraints}
            />
          )}
          {!run && !selectedNode && (
            <div className="panel p-4 text-xs text-[var(--text-dim)]">
              The decision pane fills after a simulation run: containment sets with costs and constraints,
              rejected sets with reasons, and evidence requests. Click any node for its evidence.
            </div>
          )}
        </div>
      </div>

      {/* Bottom tabs */}
      {run && (
        <div className="space-y-2">
          <div className="flex gap-2 text-xs">
            {(["pathways", "disagreement", "unknowns", "case"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)} data-testid={`tab-${t}`}
                className={`rounded border px-3 py-1 ${tab === t ? "border-[var(--amber)] text-[var(--amber)]" : "border-[var(--border)] text-[var(--text-dim)]"}`}>
                {t === "case" ? "Case file" : t === "unknowns" ? `Unknowns (${run.unknowns.unknowns.length})` : t}
              </button>
            ))}
          </div>

          {tab === "pathways" && (
            <div className="panel p-3 text-xs" data-testid="pathways-panel">
              <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
                Impact pathways <span className="label-simulated normal-case">(model result)</span>
              </h3>
              {caseFile.top_pathways.map((p: Json) => (
                <div key={p.pathway_id} className="inset mb-1.5 p-2">
                  <span className="text-[var(--text)]">{p.description}</span>
                  <span className="ml-2 text-[var(--text-dim)]">
                    strength {p.strength} · first impact {fmtMin(p.first_impact_minutes)}
                  </span>
                </div>
              ))}
              <h3 className="mb-1 mt-3 font-semibold uppercase tracking-wider text-[var(--text-dim)]">Impact events</h3>
              <div className="max-h-56 overflow-y-auto">
                {caseFile.impact_timeline.map((e: Json) => (
                  <div key={e.impact_event_id} className="border-t border-[var(--border)] py-1 text-[var(--text-dim)]">
                    <span className="text-[var(--text)]">{fmtMin(e.impact_start_minutes)}</span> — {e.target_node_id}{" "}
                    peaks at {(e.magnitude * 100).toFixed(0)}% via{" "}
                    {e.source_kind === "incident" ? `incident ${e.source_node_id}` : `${e.source_node_id} (${e.via_edge_id})`}
                    <details className="inline"><summary className="ml-1 inline cursor-pointer text-[var(--blue)]">rule</summary>
                      <div className="label-simulated">{e.rule} · assumptions: {e.assumption_ids.join(", ")}</div>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "disagreement" && <DisagreementPanel report={run.disagreement} comparables={run.comparables} />}

          {tab === "unknowns" && (
            <div className="panel p-3 text-xs" data-testid="unknowns-panel">
              <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
                Unknowns & uncertainty
              </h3>
              <div className="inset mb-2 p-2">
                <div className="mb-1 font-semibold text-[var(--amber)]">
                  Reliability: {run.unknowns.reliability_label}
                </div>
                {Object.entries(run.unknowns.uncertainty)
                  .filter(([k]) => ["aleatoric", "epistemic", "observability", "model_disagreement"].includes(k))
                  .map(([k, v]) => (
                    <div key={k} className="flex items-center gap-2">
                      <span className="w-36 text-[var(--text-dim)]">{k}</span>
                      <div className="h-1.5 w-40 rounded bg-[var(--bg)]">
                        <div className="h-1.5 rounded bg-[var(--violet)]" style={{ width: `${Number(v) * 100}%` }} />
                      </div>
                      <span>{Number(v).toFixed(2)}</span>
                    </div>
                  ))}
                <div className="mt-1 text-[var(--text-dim)]">{run.unknowns.uncertainty.explanation}</div>
              </div>
              {run.unknowns.unknowns.map((u: Json, i: number) => (
                <div key={i} className="inset mb-1.5 p-2">
                  <span className="label-unknown">[{u.kind}]</span> {u.detail}
                </div>
              ))}
              <h3 className="mb-1 mt-3 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
                Evidence requests (next best information)
              </h3>
              {caseFile.evidence_requests.map((r: Json, i: number) => (
                <div key={i} className="inset mb-1.5 p-2">
                  <div className="text-[var(--blue)]">{r.request}</div>
                  <div className="text-[var(--text-dim)]">
                    {r.reason} · ~${r.estimated_cost_usd.toLocaleString()} · ~{fmtMin(r.estimated_time_minutes)} ·
                    targets {r.uncertainty_target}
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "case" && <CaseFileExport caseFile={caseFile} />}
        </div>
      )}
    </div>
  );
}
