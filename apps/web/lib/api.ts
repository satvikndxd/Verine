/** API client + shared types for the VERINE NERVE backend. */

export interface Capability {
  capability_id: string;
  name: string;
  description: string;
  minimum_service_level: number;
  target_service_level: number;
  unit: string;
  criticality: string;
}

export interface GraphNode {
  node_id: string;
  node_type: string;
  name: string;
  criticality: string;
  capacity: number | null;
  capacity_unit: string | null;
  recovery_time_minutes: number;
  substitutability: number;
  observability: number;
  epistemic_status: string;
  evidence_ids: string[];
}

export interface GraphEdge {
  edge_id: string;
  from_node: string;
  to_node: string;
  edge_type: string;
  criticality_weight: number;
  capacity_fraction: number;
  propagation_lag_minutes: { min: number; median: number; max: number };
  substitution_options: string[];
  epistemic_status: string;
  confidence: number;
  evidence_ids: string[];
}

export interface Snapshot {
  graph_snapshot_id: string;
  capabilities: Capability[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Incident {
  incident_id: string;
  name: string;
  incident_type: string;
  duration_minutes: number;
  severity: number;
  components: {
    target_node_id: string;
    mode: string;
    severity: number;
    duration_minutes: number;
    onset_offset_minutes?: number;
    evidence_status: string;
  }[];
}

export interface Action {
  action_id: string;
  name: string;
  action_type: string;
  target_nodes: string[];
  cost: number;
  duration_minutes: number;
  required_roles: string[];
  capacity_effect: number;
  reversibility: number;
  collateral_risk: number;
  feasibility_constraints: string[];
  side_effects: string[];
}

export interface StepState {
  t_minutes: number;
  service_levels: Record<string, number>;
  node_degradation: Record<string, number>;
  active_incident_nodes: string[];
  effective_actions: string[];
}

export interface Constraints {
  budget: number;
  deadline_minutes: number;
  minimum_service_level: number;
  available_roles: string[];
  max_collateral_risk: number;
  facts: string[];
}

// Loose typing for large nested payloads.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Json = any;

export async function api<T = Json>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = body.message ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const fmtPct = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`;

export const fmtMin = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : v >= 60 ? `${Math.floor(v / 60)}h ${v % 60}m` : `${v}m`;

export const epistemicColor = (status: string): string =>
  status === "observed"
    ? "var(--blue)"
    : status === "inferred" || status === "hypothesis"
      ? "var(--amber)"
      : status === "simulated" || status === "model_result"
        ? "var(--violet)"
        : "var(--gray)";

export const severityColor = (deg: number): string =>
  deg > 0.5 ? "var(--red)" : deg > 0.2 ? "var(--amber)" : deg > 0.05 ? "#b9a35e" : "var(--green)";
