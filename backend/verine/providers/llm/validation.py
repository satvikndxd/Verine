"""Structured-output validation and citation enforcement.

Rule (product principle 5.2 / 11.5): a factual sentence without an evidence ID
is rejected or explicitly marked unsupported — never silently passed."""

from __future__ import annotations

import json

STRUCTURED_SCHEMAS = {
    "IncidentSummary": {
        "required": ["title", "what_was_observed", "what_is_inferred", "what_is_simulated",
                     "unknowns", "evidence_ids", "confidence_status"],
        "list_fields": ["what_was_observed", "what_is_inferred", "what_is_simulated",
                        "unknowns", "alternative_explanations", "evidence_ids"],
        "cited_fields": ["what_was_observed"],
    },
    "PathwayNarration": {
        "required": ["title", "narrative_steps", "evidence_ids", "confidence_status"],
        "list_fields": ["narrative_steps", "evidence_ids"],
        "cited_fields": ["narrative_steps"],
    },
    "EvidenceGap": {
        "required": ["gaps", "evidence_ids"],
        "list_fields": ["gaps", "evidence_ids"],
        "cited_fields": [],
    },
}


def validate_structured_output(
    content: str,
    schema_name: str,
    known_evidence_ids: set[str],
) -> dict:
    """Return {valid, structured, errors, unsupported_claims}."""
    result: dict = {"valid": False, "structured": None, "errors": [], "unsupported_claims": []}

    try:
        structured = json.loads(content)
    except json.JSONDecodeError as e:
        result["errors"].append(f"Output is not valid JSON: {e}")
        return result
    if not isinstance(structured, dict):
        result["errors"].append("Output must be a JSON object")
        return result

    schema = STRUCTURED_SCHEMAS.get(schema_name)
    if schema is None:
        result["errors"].append(f"Unknown schema {schema_name!r}")
        return result

    for field in schema["required"]:
        if field not in structured:
            result["errors"].append(f"Missing required field {field!r}")
    for field in schema["list_fields"]:
        if field in structured and not isinstance(structured[field], list):
            result["errors"].append(f"Field {field!r} must be a list")

    # Citation enforcement: every cited evidence id must exist in the case.
    cited = structured.get("evidence_ids", [])
    if isinstance(cited, list):
        unknown = [e for e in cited if e not in known_evidence_ids]
        if unknown:
            result["errors"].append(f"Cited evidence ids not in case: {unknown}")

    # Factual claims: items in cited_fields must be dicts {claim, evidence_ids}
    # or strings (then they inherit top-level citations; if none, unsupported).
    for field in schema["cited_fields"]:
        for item in structured.get(field, []) or []:
            if isinstance(item, dict):
                ids = item.get("evidence_ids", [])
                if not ids or any(e not in known_evidence_ids for e in ids):
                    result["unsupported_claims"].append(item.get("claim", str(item)))
            elif isinstance(item, str):
                if not cited:
                    result["unsupported_claims"].append(item)

    if result["unsupported_claims"]:
        # Do not fail the whole response; mark claims and force honesty.
        structured["unsupported_claims"] = result["unsupported_claims"]

    result["valid"] = not result["errors"]
    result["structured"] = structured if result["valid"] else None
    return result
