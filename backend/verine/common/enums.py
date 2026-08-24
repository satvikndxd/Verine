"""Domain enums. Unknown values must fail validation."""

from __future__ import annotations

from enum import Enum


class EpistemicStatus(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    SIMULATED = "simulated"
    MODEL_RESULT = "model_result"
    HYPOTHESIS = "hypothesis"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class NodeType(str, Enum):
    CAPABILITY = "capability"
    SERVICE = "service"
    APPLICATION = "application"
    API = "api"
    VENDOR = "vendor"
    CLOUD_REGION = "cloud_region"
    DATA_STORE = "data_store"
    QUEUE = "queue"
    IDENTITY_PROVIDER = "identity_provider"
    PROCESS = "process"
    TEAM = "team"
    PERSON_ROLE = "person_role"
    FACILITY = "facility"
    GEOGRAPHY = "geography"
    CONTRACT = "contract"
    CONTROL = "control"
    ASSET = "asset"
    INCIDENT_SOURCE = "incident_source"
    EXTERNAL_CONDITION = "external_condition"


class EdgeType(str, Enum):
    REQUIRES = "requires"
    CALLS = "calls"
    STORES_IN = "stores_in"
    AUTHENTICATES_WITH = "authenticates_with"
    OPERATED_BY = "operated_by"
    SUPPLIED_BY = "supplied_by"
    LOCATED_IN = "located_in"
    MONITORED_BY = "monitored_by"
    RECOVERS_THROUGH = "recovers_through"
    CONSTRAINED_BY = "constrained_by"
    SUBSTITUTES_FOR = "substitutes_for"
    COMMUNICATES_THROUGH = "communicates_through"
    DEPENDS_ON = "depends_on"


class Criticality(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NodeStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class IncidentMode(str, Enum):
    LATENCY = "latency"
    CAPACITY_REDUCTION = "capacity_reduction"
    UNAVAILABLE = "unavailable"
    DATA_LOSS = "data_loss"
    COMMUNICATION_FAILURE = "communication_failure"


class IncidentType(str, Enum):
    SINGLE = "single"
    COMPOUND = "compound"


class ActionType(str, Enum):
    REROUTE = "reroute"
    SCALE = "scale"
    ISOLATE = "isolate"
    DEGRADE_GRACEFULLY = "degrade_gracefully"
    COMMUNICATE = "communicate"
    MANUAL_PROCESS = "manual_process"
    RESTORE = "restore"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Severity multipliers used by the propagation engine per incident mode.
# These are SIMULATION RULES for synthetic scenarios, not causal estimates.
INCIDENT_MODE_MULTIPLIER = {
    IncidentMode.UNAVAILABLE: 1.0,
    IncidentMode.CAPACITY_REDUCTION: 1.0,
    IncidentMode.DATA_LOSS: 0.9,
    IncidentMode.LATENCY: 0.7,
    IncidentMode.COMMUNICATION_FAILURE: 0.6,
}
