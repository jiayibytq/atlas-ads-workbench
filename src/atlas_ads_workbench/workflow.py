"""Stable workflow selection for progressive seller intake."""

from typing import Any, List


class WorkflowValidationError(ValueError):
    """Raised when the seller workflow selection is invalid."""


SUPPORTED_AD_MODULES = ("sp", "sb", "sd", "sd_cross_sell")


def normalize_selected_ad_modules(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise WorkflowValidationError("selected_ad_modules must be an array of strings")
    unknown = sorted(set(value) - set(SUPPORTED_AD_MODULES))
    if unknown:
        raise WorkflowValidationError(
            "unsupported advertising module: %s" % ", ".join(unknown)
        )
    return [module for module in SUPPORTED_AD_MODULES if module in value]
