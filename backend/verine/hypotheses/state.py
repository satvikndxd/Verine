"""Hypothesis state machine (master prompt §12.3). Transitions are audited;
external evidence NEVER auto-promotes to confirmed internal impact."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

STATES = [
    "UNCONFIRMED",
    "OBSERVED_EXTERNAL_SIGNAL",
    "CORROBORATED",
    "OPERATIONALLY_RELEVANT_HYPOTHESIS",
    "CONTESTED",
    "RESOLVED_EXTERNAL_EVENT",
    "USER_CONFIRMED_IMPACT",
]

# Transitions allowed WITHOUT a human actor (signal-driven).
AUTO_TRANSITIONS = {
    ("UNCONFIRMED", "OBSERVED_EXTERNAL_SIGNAL"),
    ("UNCONFIRMED", "CORROBORATED"),
    ("UNCONFIRMED", "OPERATIONALLY_RELEVANT_HYPOTHESIS"),
    ("OBSERVED_EXTERNAL_SIGNAL", "CORROBORATED"),
    ("OBSERVED_EXTERNAL_SIGNAL", "OPERATIONALLY_RELEVANT_HYPOTHESIS"),
    ("CORROBORATED", "OPERATIONALLY_RELEVANT_HYPOTHESIS"),
    ("OBSERVED_EXTERNAL_SIGNAL", "CONTESTED"),
    ("CORROBORATED", "CONTESTED"),
    ("OPERATIONALLY_RELEVANT_HYPOTHESIS", "CONTESTED"),
    ("CONTESTED", "CORROBORATED"),
    ("OBSERVED_EXTERNAL_SIGNAL", "RESOLVED_EXTERNAL_EVENT"),
    ("CORROBORATED", "RESOLVED_EXTERNAL_EVENT"),
    ("OPERATIONALLY_RELEVANT_HYPOTHESIS", "RESOLVED_EXTERNAL_EVENT"),
}

# Transitions that REQUIRE an explicit human actor + reason.
HUMAN_TRANSITIONS = {
    ("OBSERVED_EXTERNAL_SIGNAL", "USER_CONFIRMED_IMPACT"),
    ("CORROBORATED", "USER_CONFIRMED_IMPACT"),
    ("OPERATIONALLY_RELEVANT_HYPOTHESIS", "USER_CONFIRMED_IMPACT"),
    ("CONTESTED", "USER_CONFIRMED_IMPACT"),
}


class TransitionError(Exception):
    pass


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    watch_pack_id: str
    capability_id: str
    title: str
    state: str = "UNCONFIRMED"
    signal_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    node_matches: list[dict] = Field(default_factory=list)
    independence_groups: list[str] = Field(default_factory=list)
    quorum: dict = Field(default_factory=dict)
    shadow_edge_ids: list[str] = Field(default_factory=list)
    analysis_run_id: str | None = None
    case_file_id: str | None = None
    cascade_clock: dict | None = None
    contradictions: list[str] = Field(default_factory=list)
    window_start_at: str = ""
    window_end_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    audit: list[dict] = Field(default_factory=list)

    def transition(self, to_state: str, actor: str, reason: str, at: str) -> None:
        if to_state == self.state:
            return
        pair = (self.state, to_state)
        if pair in AUTO_TRANSITIONS:
            pass
        elif pair in HUMAN_TRANSITIONS:
            if actor in ("system", ""):
                raise TransitionError(
                    f"{self.state} -> {to_state} requires an explicit human actor and reason"
                )
            if not reason:
                raise TransitionError(f"{self.state} -> {to_state} requires a reason")
        else:
            raise TransitionError(f"Illegal transition {self.state} -> {to_state}")
        self.audit.append(
            {"from": self.state, "to": to_state, "actor": actor, "reason": reason, "at": at}
        )
        self.state = to_state
        self.updated_at = at
