"use client";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="panel p-6 text-center text-sm text-[var(--text-dim)]">{label}</div>;
}

export function ErrorBox({ error, retry }: { error: string; retry?: () => void }) {
  return (
    <div className="panel border-[var(--red)] p-4 text-sm" role="alert">
      <div className="mb-1 font-semibold text-[var(--red)]">Something failed</div>
      <div className="text-[var(--text-dim)]">{error}</div>
      {retry && (
        <button onClick={retry} className="mt-2 rounded border border-[var(--border)] px-3 py-1 text-xs hover:border-[var(--amber)]">
          Retry
        </button>
      )}
    </div>
  );
}
