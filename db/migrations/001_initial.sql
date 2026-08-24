-- VERINE NERVE initial schema (PostgreSQL).
-- NOTE (ADR-001): the v0.1 sandbox runs a file-backed JSON store behind the same
-- repository interface; this migration is kept in sync with the Pydantic
-- contracts so a Postgres repository can be swapped in without domain changes.

create table capabilities (
  id text primary key,
  name text not null,
  description text not null,
  owner_role text not null,
  minimum_service_level numeric not null check (minimum_service_level between 0 and 1),
  target_service_level numeric not null check (target_service_level between 0 and 1),
  criticality text not null,
  valid_from timestamptz not null,
  valid_to timestamptz,
  evidence_ids jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  check (minimum_service_level <= target_service_level)
);

create table graph_snapshots (
  id text primary key,
  version text not null,
  graph_json jsonb not null,
  graph_hash text not null unique,
  epistemic_summary jsonb not null,
  created_at timestamptz not null default now()
);

create table incidents (
  id text primary key,
  name text not null,
  incident_type text not null,
  onset_at timestamptz not null,
  duration_minutes integer not null check (duration_minutes > 0),
  severity numeric not null check (severity between 0 and 1),
  components_json jsonb not null,
  evidence_ids jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table scenarios (
  id text primary key,
  capability_id text not null references capabilities(id),
  graph_snapshot_id text not null references graph_snapshots(id),
  incident_id text not null references incidents(id),
  constraints_json jsonb not null,
  seed bigint not null,
  model_set jsonb not null,
  scenario_hash text not null unique,
  scenario_json jsonb not null,
  created_at timestamptz not null default now()
);

create table simulation_runs (
  id text primary key,
  scenario_id text not null references scenarios(id),
  model_id text not null,
  seed bigint not null,
  result_json jsonb not null,
  run_hash text not null unique,
  status text not null,
  started_at timestamptz not null,
  completed_at timestamptz,
  error_json jsonb
);

create table case_files (
  id text primary key,
  scenario_id text not null references scenarios(id),
  case_type text not null,
  case_json jsonb not null,
  case_hash text not null unique,
  created_at timestamptz not null default now()
);

create table evidence (
  id text primary key,
  label text not null,
  epistemic_status text not null,
  source_uri text,
  locator_json jsonb,
  content_hash text,
  statement text not null,
  created_at timestamptz not null default now()
);

create index idx_scenarios_capability on scenarios(capability_id);
create index idx_runs_scenario on simulation_runs(scenario_id);
create index idx_cases_scenario on case_files(scenario_id);
