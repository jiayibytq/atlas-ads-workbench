"""Source-neutral evidence envelopes for seller, spreadsheet, and MCP inputs."""

from typing import Any, Dict, Mapping


class EvidenceValidationError(ValueError):
    """Raised when evidence cannot safely participate in a gate."""


VALID_STATUSES = {"confirmed", "verified", "external_evidence"}
EXTERNAL_SOURCES = {"amazon_ads_mcp", "seller_spreadsheet", "catalog_mcp", "inventory_mcp"}


def normalize_evidence_context(
    raw_context: Mapping[str, Any], default_captured_at: str
) -> Dict[str, Dict[str, Any]]:
    """Normalize evidence and prevent seller input from impersonating verification."""

    if not isinstance(raw_context, Mapping):
        raise EvidenceValidationError("evidence context must be an object")
    normalized = {}
    for field, item in raw_context.items():
        if not isinstance(item, Mapping):
            raise EvidenceValidationError("%s evidence must be an object" % field)
        status = item.get("status", "confirmed")
        source = item.get("source", "seller_input")
        captured_at = item.get("captured_at", default_captured_at)
        if status not in VALID_STATUSES:
            raise EvidenceValidationError("%s has an unsupported status" % field)
        if status in {"verified", "external_evidence"} and source not in EXTERNAL_SOURCES:
            raise EvidenceValidationError(
                "%s verified evidence requires an external source" % field
            )
        if not captured_at:
            raise EvidenceValidationError("%s requires captured_at" % field)
        normalized[field] = {
            "value": item.get("value"),
            "status": status,
            "source": source,
            "captured_at": captured_at,
        }
    return normalized
