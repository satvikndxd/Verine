"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, Json, Snapshot } from "@/lib/api";
import { VerineEvent, eventColor, fmtInterval, vget, vpost } from "@/lib/verine";
import { Loading, ErrorBox } from "@/components/AsyncState";
import GraphExplorer from "@/components/GraphExplorer";
import LLMExplanation from "@/components/LLMExplanation";
import ForkCompare from "@/components/ForkCompare";

const WP = "wp_digital_payments";

export default function LiveWarRoom() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [events, setEvents] = useState<VerineEvent[]>([]);
  const [hypotheses, setHypotheses] = useState<Json[]>([]);
  const [shadows, setShadows] = useState<Json[]>([]);
  const [status, setStatus] = useState<Json | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"cascade" | "forks" | "llm" | "evidence">("cascade");
  const esRef = useRef<EventSource | null>(null);

  const refresh = useCallback(async () => {
    const [h, sh, st] = await Promise.all([
      vget<Json[]>("/hypotheses"),
      vget<Json[]>("/shadow-edges"),
      vget(`/watch-packs/${WP}/status`),
    ]);
    setHypotheses(h);
    setShadows(sh);
    setStatus(st);
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      const meta = await api("/api/presets");
      const snap = await api(`/api/graph/snapshots/${meta.graph_snapshot_id}`);
      setSnapshot(snap.graph_json);
      const evs = await vget<{ events: VerineEvent[] }>(`/streams/${WP}/events?limit=500`);
      setEvents(evs.events);
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  }, [refresh]);

  useEffect(() => {
    load();
  }, [load]);

  // Live SSE subscription (works after the first poll; heartbeats keep it warm).
  useEffect(() => {
    const es = new EventSource(`/api/verine/streams/${WP}`);
    esRef.current = es;
    const onEvt = (e: MessageEvent) => {
      try {
        const rec = JSON.parse(e.data);
        if (rec.seq) {
          setEvents((prev) => (prev.some((p) => p.seq === rec.seq) ? prev : [...prev, rec]));
          if (["hypothesis_created", "hypothesis_updated", "cascade_clock_updated",
               "shadow_edge_created", "case_saved"].includes(rec.event)) {
            refresh();
          }
        }
      } catch { /* heartbeat */ }
    };
    ["signal_observed", "hypothesis_created", "hypothesis_updated", "shadow_edge_created",
     "cascade_clock_updated", "case_saved", "connector_success", "connector_error",
     "impact_recomputed", "signal_deduplicated"].forEach((t) => es.addEventListener(t, onEvt));
    es.onerror = () => { /* browser auto-reconnects with Last-Event-ID */ };
    return () => es.close();
  }, [refresh]);

  const poll = async () => {
    setPolling(true);
    setError(null);
    try {
      await vpost(`/watch-packs/${WP}/poll`);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setPolling(false);
    }
  };

  const hyp = useMemo(
    () => hypotheses.find((h) => h.cascade_clock) ?? hypotheses[0] ?? null,
    [hypotheses],
  );

  const degradation = useMemo(() => {
    // Peak degradation from the case's blast radius, if available.
    const peak = hyp?.cascade_clock ? {} : {};
    return peak as Record<string, number>;
  }, [hyp]);

  const shadowTargets = useMemo<Set<string>>(() => new Set<string>(shadows.map((s) => String(s.to_node_id))), [shadows]);
  const matchedNodes = useMemo(
    () => new Set<string>((hyp?.node_matches ?? []).map((m: Json) => String(m.node_id))),
    [hyp],
  );

  if (error && !snapshot) return <ErrorBox error={error} retry={load} />;
  if (!snapshot) return <Loading label="Loading capability graph…" />;

  const liveEnabled = status?.connectors?.some((c: Json) => !c.fixture_mode);
  const statusLabel = !events.length ? "NO RECENT SIGNAL"
    : liveEnabled ? "LIVE" : "OFFLINE FIXTURES";

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="panel flex flex-wrap items-center gap-3 px-4 py-2 text-sm">
        <span className="font-bold tracking-wide">VERINE LIVE</span>
        <span className="text-[var(--text-dim)]">Digital Payments Authorization</span>
        <span className="badge" style={{ color: statusLabel === "LIVE" ? "var(--green)" : "var(--violet)" }}
          data-testid="live-status">{statusLabel}</span>
        {hyp?.state && (
          <span className="badge" style={{ color: "var(--amber)" }} data-testid="hypothesis-state">
            {hyp.state}
          </span>
        )}
        <span className="ml-auto flex items-center gap-2">
          <span className="text-xs text-[var(--text-dim)]">
            signals {status?.signal_count ?? 0} · hypotheses {status?.hypothesis_count ?? 0} · shadow {shadows.length}
          </span>
          <button onClick={poll} disabled={polling} data-testid="poll-button"
            className="rounded bg-[var(--amber)] px-4 py-1.5 font-semibold text-black hover:opacity-90 disabled:opacity-50">
            {polling ? "Polling…" : "Poll connectors"}
          </button>
        </span>
      </div>
      {error && <ErrorBox error={error} retry={poll} />}

      <div className="grid grid-cols-12 gap-3">
        {/* Left: capability + quorum + shadow */}
        <div className="col-span-3 space-y-3">
          <div className="panel p-3 text-xs" data-testid="capability-pane">
            <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">Capability</h3>
            {hyp ? (
              <>
                <div className="mb-2">
                  <div className="text-[var(--text-dim)]">Quorum</div>
                  <div className="text-lg font-bold text-[var(--text)]" data-testid="quorum">
                    {hyp.quorum?.independent_group_count ?? 0} independent group(s)
                  </div>
                  <div className="text-[10px] text-[var(--text-dim)]">
                    {(hyp.quorum?.independent_groups ?? []).join(", ")}
                  </div>
                </div>
                <div className="mb-2">
                  <div className="text-[var(--text-dim)]">Signals in hypothesis</div>
                  <div className="font-semibold">{hyp.signal_ids?.length ?? 0}</div>
                </div>
                <div>
                  <div className="text-[var(--text-dim)]">Mapped nodes</div>
                  <div className="font-semibold">{hyp.node_matches?.length ?? 0}</div>
                </div>
              </>
            ) : (
              <div className="text-[var(--text-dim)]">
                No hypothesis yet. Click <span className="text-[var(--amber)]">Poll connectors</span> to
                ingest the offline fixture signals.
              </div>
            )}
          </div>

          <div className="panel p-3 text-xs" data-testid="shadow-pane">
            <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
              Shadowgraph <span className="label-simulated normal-case">(review required)</span>
            </h3>
            {shadows.length === 0 && <div className="text-[var(--text-dim)]">No shadow edges proposed.</div>}
            {shadows.map((s) => (
              <div key={s.shadow_edge_id} className="inset mb-1.5 p-2">
                <span className="label-simulated">{s.from_node_id}</span> ⇢{" "}
                <span className="label-simulated">{s.to_node_id}</span>
                <div className="text-[var(--text-dim)]">{s.reason}</div>
                <div className="text-[var(--amber)]">confidence {s.confidence} · inferred, not confirmed</div>
              </div>
            ))}
          </div>
        </div>

        {/* Center: graph + event tape */}
        <div className="col-span-6 space-y-3">
          <div className="panel overflow-hidden">
            <GraphExplorer
              snapshot={snapshot}
              degradation={degradation}
              hiddenEdgeIds={[]}
              incidentTargets={[...matchedNodes]}
              selectedNodeId={selectedNode}
              onSelectNode={setSelectedNode}
              layerFilter={{ observed: true, inferred: true, simulated: true, unknown: true }}
            />
            <div className="border-t border-[var(--border)] px-3 py-1.5 text-[10px] text-[var(--text-dim)]">
              Red ring = signal-mapped node. Violet shadow targets ({[...shadowTargets].join(", ") || "none"})
              are inferred shared dependencies, review-required.
            </div>
          </div>

          <div className="panel p-3" data-testid="event-tape">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)]">
              Event tape
            </h3>
            <div className="max-h-56 space-y-0.5 overflow-y-auto font-mono text-[11px]">
              {events.slice().reverse().map((e) => (
                <div key={e.seq} className="flex gap-2">
                  <span className="text-[var(--text-dim)]">{e.at?.slice(11, 19)}</span>
                  <span style={{ color: eventColor(e.event) }}>{e.event}</span>
                  <span className="truncate text-[var(--text-dim)]">
                    {e.data?.title || e.data?.statement || e.data?.provider_id || e.data?.hypothesis_id || ""}
                  </span>
                </div>
              ))}
              {!events.length && <div className="text-[var(--text-dim)]">No events yet.</div>}
            </div>
          </div>
        </div>

        {/* Right: decision tabs */}
        <div className="col-span-3 space-y-3">
          <div className="flex flex-wrap gap-1 text-xs">
            {(["cascade", "forks", "llm", "evidence"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)} data-testid={`tab-${t}`}
                className={`rounded border px-2 py-1 ${tab === t ? "border-[var(--amber)] text-[var(--amber)]" : "border-[var(--border)] text-[var(--text-dim)]"}`}>
                {t}
              </button>
            ))}
          </div>

          {tab === "cascade" && (
            <div className="panel p-3 text-xs" data-testid="cascade-pane">
              <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
                Cascade clock <span className="label-simulated normal-case">(model result)</span>
              </h3>
              {hyp?.cascade_clock ? (
                <>
                  <p className="mb-2 text-[var(--text)]">{hyp.cascade_clock.statement}</p>
                  <div className="space-y-1 text-[var(--text-dim)]">
                    <Row label="Next node" v={fmtInterval(hyp.cascade_clock.next_node)} />
                    <Row label="Capability floor" v={fmtInterval(hyp.cascade_clock.capability_floor)} />
                    <Row label="Recovery" v={fmtInterval(hyp.cascade_clock.recovery)} />
                    {hyp.cascade_clock.floor_breach_fraction !== null && (
                      <Row label="Floor breach (MC)"
                        v={`${Math.round(hyp.cascade_clock.floor_breach_fraction * 100)}% of reps`} />
                    )}
                  </div>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-[var(--blue)]">Assumptions</summary>
                    <ul className="mt-1 list-disc pl-4 text-[var(--text-dim)]">
                      {(hyp.cascade_clock.assumptions ?? []).map((a: string, i: number) => <li key={i}>{a}</li>)}
                    </ul>
                  </details>
                  {hyp.case_file_id && (
                    <div className="mt-2 text-[10px] text-[var(--text-dim)]">
                      Case: <span className="text-[var(--green)]">{hyp.case_file_id}</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-[var(--text-dim)]">
                  No cascade projection yet. Operational signals (provider/weather) drive the clock;
                  vulnerability signals stay context-only.
                </div>
              )}
            </div>
          )}

          {tab === "forks" && hyp?.case_file_id && <ForkCompare caseId={hyp.case_file_id} watchPackId={WP} />}
          {tab === "forks" && !hyp?.case_file_id && (
            <div className="panel p-3 text-xs text-[var(--text-dim)]">Run a poll to produce a case to fork.</div>
          )}

          {tab === "llm" && hyp && <LLMExplanation hypothesisId={hyp.hypothesis_id} watchPackId={WP} />}
          {tab === "llm" && !hyp && (
            <div className="panel p-3 text-xs text-[var(--text-dim)]">No hypothesis to explain yet.</div>
          )}

          {tab === "evidence" && (
            <div className="panel p-3 text-xs" data-testid="evidence-pane">
              <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
                Signals &amp; impact status
              </h3>
              <SignalList />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, v }: { label: string; v: string }) {
  return (
    <div className="flex justify-between">
      <span>{label}</span>
      <span className="text-[var(--text)]">{v}</span>
    </div>
  );
}

function SignalList() {
  const [signals, setSignals] = useState<Json[]>([]);
  useEffect(() => {
    vget<Json[]>("/signals").then(setSignals).catch(() => {});
  }, []);
  return (
    <div className="space-y-1.5">
      {signals.map((s) => (
        <div key={s.signal_id} className="inset p-2">
          <div className="flex justify-between">
            <span className="label-observed">{s.signal_type}</span>
            <span className="text-[var(--amber)]">{s.impact_status}</span>
          </div>
          <div className="text-[var(--text)]">{s.title}</div>
          <div className="text-[10px] text-[var(--text-dim)]">
            published {s.published_at} · {s.raw_artifact_hash?.slice(0, 20)}…
          </div>
        </div>
      ))}
      {!signals.length && <div className="text-[var(--text-dim)]">No signals yet.</div>}
    </div>
  );
}
