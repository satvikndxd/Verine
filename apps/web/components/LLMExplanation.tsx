"use client";

import { useEffect, useState } from "react";
import { Json } from "@/lib/api";
import { vget, vpost } from "@/lib/verine";

/** Optional, cited LLM explanation. Requires a configured credential; the war
 * room is fully functional without it. An LLM failure never breaks the page. */
export default function LLMExplanation({ hypothesisId, watchPackId }: { hypothesisId: string; watchPackId: string }) {
  const [creds, setCreds] = useState<Json[]>([]);
  const [credId, setCredId] = useState("");
  const [models, setModels] = useState<Json[]>([]);
  const [model, setModel] = useState("");
  const [result, setResult] = useState<Json | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    vget<Json[]>("/credentials").then((cs) => {
      setCreds(cs);
      if (cs[0]) setCredId(cs[0].credential_id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!credId) return;
    const c = creds.find((x) => x.credential_id === credId);
    if (!c) return;
    vget(`/providers/${c.provider_id}/models?credential_id=${credId}`)
      .then((r) => { setModels(r.models); if (r.models[0]) setModel(r.models[0].model_id); })
      .catch(() => setModels([]));
  }, [credId, creds]);

  const explain = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await vpost("/llm/complete", {
        credential_id: credId, model, task: "incident_summarize",
        hypothesis_id: hypothesisId, watch_pack_id: watchPackId,
      });
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!creds.length) {
    return (
      <div className="panel p-3 text-xs text-[var(--text-dim)]" data-testid="llm-pane">
        No AI provider configured. Add a key under <span className="text-[var(--amber)]">AI Providers</span> to
        get a cited explanation. The deterministic analysis above does not require it.
      </div>
    );
  }

  const s = result?.structured;
  return (
    <div className="panel p-3 text-xs" data-testid="llm-pane">
      <h3 className="mb-2 font-semibold uppercase tracking-wider text-[var(--text-dim)]">
        LLM explanation <span className="label-simulated normal-case">(cited, optional)</span>
      </h3>
      <div className="mb-2 flex flex-wrap gap-1">
        <select value={credId} onChange={(e) => setCredId(e.target.value)} className="inset px-1 py-0.5">
          {creds.map((c) => <option key={c.credential_id} value={c.credential_id}>{c.provider_id}</option>)}
        </select>
        <select value={model} onChange={(e) => setModel(e.target.value)} className="inset px-1 py-0.5">
          {models.map((m) => <option key={m.model_id} value={m.model_id}>{m.model_id}</option>)}
        </select>
        <button onClick={explain} disabled={busy || !model} data-testid="explain-button"
          className="rounded bg-[var(--amber)] px-3 py-0.5 font-semibold text-black disabled:opacity-50">
          {busy ? "Explaining…" : "Explain"}
        </button>
      </div>
      {error && <div className="text-[var(--red)]">{error}</div>}
      {s && (
        <div className="space-y-1.5" data-testid="llm-result">
          <div className="font-semibold text-[var(--text)]">{s.title}</div>
          {result.validation?.valid
            ? <span className="badge" style={{ color: "var(--green)" }}>schema valid · cited</span>
            : <span className="badge" style={{ color: "var(--red)" }}>validation failed</span>}
          <Section title="Observed" items={(s.what_was_observed ?? []).map((o: Json) =>
            typeof o === "string" ? o : `${o.claim} [${(o.evidence_ids ?? []).join(", ")}]`)} color="var(--blue)" />
          <Section title="Inferred" items={s.what_is_inferred ?? []} color="var(--amber)" />
          <Section title="Simulated" items={s.what_is_simulated ?? []} color="var(--violet)" />
          <Section title="Unknowns" items={s.unknowns ?? []} color="var(--gray)" />
          {s.unsupported_claims?.length > 0 && (
            <Section title="Unsupported (flagged)" items={s.unsupported_claims} color="var(--red)" />
          )}
          <div className="text-[10px] text-[var(--text-dim)]">
            confidence: {s.confidence_status} · response {result.response_hash?.slice(0, 18)}…
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ title, items, color }: { title: string; items: string[]; color: string }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className="font-semibold" style={{ color }}>{title}</div>
      <ul className="list-disc pl-4 text-[var(--text-dim)]">
        {items.map((it, i) => <li key={i}>{it}</li>)}
      </ul>
    </div>
  );
}
