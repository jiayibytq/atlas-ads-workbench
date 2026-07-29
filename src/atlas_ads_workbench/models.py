"""Validated, transparent input contracts for the local workbench."""

from typing import Any, Dict, Mapping


class IntakeValidationError(ValueError):
    """Raised when a seller-provided intake field cannot be accepted."""


MARKETPLACES = {"US", "DE", "UK", "JP"}
PRODUCT_STAGES = {"launch", "growth", "mature", "clearance"}


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise IntakeValidationError("%s is required" % field)
    return value.strip()


def _number_in_range(
    payload: Mapping[str, Any], field: str, minimum: float, maximum: float
) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IntakeValidationError("%s must be a number" % field)
    normalized = float(value)
    if not minimum <= normalized <= maximum:
        raise IntakeValidationError(
            "%s must be between %s and %s" % (field, minimum, maximum)
        )
    return normalized


def validate_intake(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a normalized seller-input snapshot or raise a field-level error.

    This contract deliberately attaches provenance metadata. It makes clear that
    phase one has not consulted a marketplace, an MCP, or a language model.
    """

    if not isinstance(payload, Mapping):
        raise IntakeValidationError("payload must be an object")

    marketplace = _required_text(payload, "marketplace").upper()
    if marketplace not in MARKETPLACES:
        raise IntakeValidationError("marketplace must be one of US, DE, UK, JP")

    product_stage = _required_text(payload, "product_stage").lower()
    if product_stage not in PRODUCT_STAGES:
        raise IntakeValidationError(
            "product_stage must be one of launch, growth, mature, clearance"
        )

    return {
        "schema_version": 1,
        "marketplace": marketplace,
        "product_stage": product_stage,
        "monthly_sales_target": _number_in_range(
            payload, "monthly_sales_target", 1, 10_000_000
        ),
        "product_price_usd": _number_in_range(
            payload, "product_price_usd", 0.01, 1_000_000
        ),
        "target_tacos_percent": _number_in_range(
            payload, "target_tacos_percent", 0.01, 100
        ),
        "ad_sales_share_percent": _number_in_range(
            payload, "ad_sales_share_percent", 1, 100
        ),
        "benchmark_cpc_usd": _number_in_range(
            payload, "benchmark_cpc_usd", 0.01, 10_000
        ),
        "benchmark_cvr_percent": _number_in_range(
            payload, "benchmark_cvr_percent", 0.01, 100
        ),
        "business_goals": _required_text(payload, "business_goals"),
        "data_source": "seller_input",
        "external_data_used": False,
        "model_calls": 0,
    }
