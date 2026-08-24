"""Watch packs: bind one capability + graph snapshot to live connectors,
entity aliases, and geography mappings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GeographyBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str  # display, e.g. "New York"
    match_terms: list[str]  # lowercase substrings matched against signal geographies
    node_id: str


class WatchPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    watch_pack_id: str
    name: str
    capability_id: str
    graph_snapshot_id: str
    connector_ids: list[str] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)  # lowercase alias -> node_id
    geographies: list[GeographyBinding] = Field(default_factory=list)
    correlation_window_minutes: int = Field(default=240, gt=0)
    status: str = "paused"  # running | paused
    auto_analysis: bool = True  # deterministic analysis only; LLM is never automatic
    created_at: str = ""
    updated_at: str = ""
