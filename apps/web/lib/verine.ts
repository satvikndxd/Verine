/** VERINE live-layer API helpers and types. */
import { api, Json } from "./api";

export interface Connector {
  connector_id: string;
  connector_type: string;
  label: string;
  enabled: boolean;
  fixture_path: string | null;
  source_strength: string;
  source_independence_group: string;
}

export interface WatchPack {
  watch_pack_id: string;
  name: string;
  capability_id: string;
  graph_snapshot_id: string;
  connector_ids: string[];
  status: string;
}

export interface CredentialMeta {
  credential_id: string;
  provider_id: string;
  label: string;
  masked: string;
  enabled: boolean;
  last_test_status: string;
  default_model: string | null;
}

export interface VerineEvent {
  seq: number;
  id: string;
  event: string;
  at: string;
  data: Json;
}

export const vget = <T = Json>(path: string) => api<T>(`/api/verine${path}`);
export const vpost = <T = Json>(path: string, body?: Json) =>
  api<T>(`/api/verine${path}`, { method: "POST", body: body ? JSON.stringify(body) : undefined });
export const vdelete = (path: string) =>
  fetch(`/api/verine${path}`, { method: "DELETE" });

export const eventColor = (type: string): string => {
  if (type.includes("error") || type.includes("failed")) return "var(--red)";
  if (type.includes("shadow")) return "var(--violet)";
  if (type.includes("hypothesis") || type.includes("cascade")) return "var(--amber)";
  if (type.includes("signal")) return "var(--blue)";
  if (type.includes("case") || type.includes("fork")) return "var(--green)";
  return "var(--text-dim)";
};

export interface Interval {
  low: number | null;
  median: number | null;
  high: number | null;
}

export const fmtInterval = (iv: Interval | null | undefined, unit = "m"): string => {
  if (!iv || iv.median === null) return "—";
  const r = (v: number | null) => (v === null ? "?" : Math.round(v));
  if (iv.low === iv.high) return `${r(iv.median)}${unit}`;
  return `${r(iv.low)}–${r(iv.high)}${unit}`;
};
