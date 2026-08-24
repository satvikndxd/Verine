"use client";

import { useEffect, useState } from "react";
import { Json } from "@/lib/api";
import { CredentialMeta, vget, vpost, vdelete } from "@/lib/verine";
import { Loading, ErrorBox } from "@/components/AsyncState";

const PROVIDERS = [
  { id: "openrouter", label: "OpenRouter", protocol: "OpenAI-compatible", needsKey: true },
  { id: "openai", label: "OpenAI", protocol: "OpenAI-compatible", needsKey: true },
  { id: "anthropic", label: "Anthropic", protocol: "Messages API", needsKey: true },
  { id: "openai_compatible", label: "Custom OpenAI-compatible", protocol: "OpenAI-compatible", needsKey: true },
  { id: "ollama_local", label: "Ollama (local)", protocol: "OpenAI-compatible", needsKey: false },
];

export default function ProvidersPage() {
  const [creds, setCreds] = useState<CredentialMeta[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openForm, setOpenForm] = useState<string | null>(null);

  const load = () => {
    setError(null);
    vget<CredentialMeta[]>("/credentials").then(setCreds).catch((e) => setError(String(e)));
  };
  useEffect(load, []);

  if (error) return <ErrorBox error={error} retry={load} />;
  if (!creds) return <Loading />;

  const byProvider: Record<string, CredentialMeta[]> = {};
  creds.forEach((c) => (byProvider[c.provider_id] ??= []).push(c));

  return (
    <div className="space-y-3">
      <div className="panel p-4">
        <h1 className="text-lg font-bold">AI Providers</h1>
        <p className="mt-1 max-w-3xl text-sm text-[var(--text-dim)]">
          Bring your own key. Keys are encrypted at rest with authenticated encryption and never
          returned to the browser, embedded in exports, or written to logs. The LLM is an optional
          explanation layer — VERINE&apos;s deterministic pipeline works with no provider configured.
        </p>
      </div>

      {PROVIDERS.map((p) => (
        <div key={p.id} className="panel p-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-semibold">{p.label}</span>
              <span className="ml-2 text-xs text-[var(--text-dim)]">Protocol: {p.protocol}</span>
            </div>
            <span className="badge" style={{ color: byProvider[p.id]?.length ? "var(--green)" : "var(--text-dim)" }}>
              {byProvider[p.id]?.length ? "CONNECTED" : p.needsKey ? "NOT CONFIGURED" : "AVAILABLE"}
            </span>
          </div>

          {byProvider[p.id]?.map((c) => (
            <CredentialRow key={c.credential_id} cred={c} onChange={load} />
          ))}

          {openForm === p.id ? (
            <AddForm provider={p} onDone={() => { setOpenForm(null); load(); }} onCancel={() => setOpenForm(null)} />
          ) : (
            <button onClick={() => setOpenForm(p.id)}
              className="mt-2 rounded border border-[var(--border)] bg-[var(--bg-inset)] px-3 py-1 text-xs hover:border-[var(--amber)]"
              data-testid={`add-${p.id}`}>
              + Add {p.label} key
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function CredentialRow({ cred, onChange }: { cred: CredentialMeta; onChange: () => void }) {
  const [testing, setTesting] = useState(false);
  const [models, setModels] = useState<Json[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const test = async () => {
    setTesting(true);
    setMsg(null);
    try {
      const r = await vpost(`/credentials/${cred.credential_id}/test`);
      setMsg(`Test: ${r.health.status}${r.health.detail ? " — " + r.health.detail : ""}`);
      onChange();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setTesting(false);
    }
  };

  const listModels = async () => {
    try {
      const r = await vget(`/providers/${cred.provider_id}/models?credential_id=${cred.credential_id}`);
      setModels(r.models);
    } catch (e) {
      setMsg(String(e));
    }
  };

  return (
    <div className="inset mt-2 p-2.5 text-xs" data-testid="credential-row">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[var(--text)]">{cred.masked}</span>
        {cred.label && <span className="text-[var(--text-dim)]">{cred.label}</span>}
        <span className="badge" style={{ color: cred.last_test_status === "success" ? "var(--green)" : "var(--text-dim)" }}>
          {cred.last_test_status}
        </span>
        <div className="ml-auto flex gap-2">
          <button onClick={test} disabled={testing} className="underline hover:text-[var(--amber)]" data-testid="test-credential">
            {testing ? "Testing…" : "Test connection"}
          </button>
          <button onClick={listModels} className="underline hover:text-[var(--blue)]">Models</button>
          <button onClick={async () => { await vdelete(`/credentials/${cred.credential_id}`); onChange(); }}
            className="underline hover:text-[var(--red)]" data-testid="delete-credential">Delete</button>
        </div>
      </div>
      {msg && <div className="mt-1 text-[var(--text-dim)]">{msg}</div>}
      {models && (
        <div className="mt-1 text-[var(--text-dim)]">
          {models.map((m: Json) => (
            <span key={m.model_id} className="mr-2">
              {m.model_id}
              <span className="text-[var(--violet)]">
                {" "}({m.prompt_cost_per_mtok !== null ? `$${m.prompt_cost_per_mtok}/Mtok` : "COST UNKNOWN"})
              </span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function AddForm({ provider, onDone, onCancel }: { provider: Json; onDone: () => void; onCancel: () => void }) {
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await vpost("/credentials", {
        provider_id: provider.id,
        api_key: key,
        label,
        base_url: baseUrl || null,
      });
      onDone();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inset mt-2 space-y-2 p-3 text-xs">
      {provider.needsKey && (
        <input type="password" placeholder="API key (stored encrypted; shown once)" value={key}
          onChange={(e) => setKey(e.target.value)} className="w-full bg-[var(--bg)] px-2 py-1"
          data-testid="key-input" />
      )}
      <input placeholder="Label (optional)" value={label} onChange={(e) => setLabel(e.target.value)}
        className="w-full bg-[var(--bg)] px-2 py-1" />
      {provider.id === "openai_compatible" && (
        <input placeholder="Base URL (https:// required in deployed mode)" value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)} className="w-full bg-[var(--bg)] px-2 py-1" />
      )}
      {provider.id === "openai_compatible" && (
        <div className="text-[var(--amber)]">
          Custom endpoints are SSRF-guarded and require explicit confirmation before any content is sent.
        </div>
      )}
      {error && <div className="text-[var(--red)]">{error}</div>}
      <div className="flex gap-2">
        <button onClick={submit} disabled={busy}
          className="rounded bg-[var(--amber)] px-3 py-1 font-semibold text-black disabled:opacity-50"
          data-testid="save-credential">
          {busy ? "Saving…" : "Save key"}
        </button>
        <button onClick={onCancel} className="rounded border border-[var(--border)] px-3 py-1">Cancel</button>
      </div>
    </div>
  );
}
