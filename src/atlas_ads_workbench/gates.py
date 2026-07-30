"""Versioned evidence gates that decide whether a rule may be evaluated."""

from typing import Any, Dict, Mapping, Sequence


VALID_EVIDENCE_STATUSES = {"confirmed", "verified", "external_evidence"}


def _evidence_passes(
    context: Mapping[str, Any], field: str, accepted_statuses: Sequence[str], accepted_values=None
) -> bool:
    item = context.get(field)
    if not isinstance(item, Mapping):
        return False
    if item.get("status") not in accepted_statuses:
        return False
    value = item.get("value")
    if value in (None, "", [], {}):
        return False
    return accepted_values is None or value in accepted_values


def _evidence_gate(
    gate_id: str, required: Sequence[Dict[str, Any]], context: Mapping[str, Any]
) -> Dict[str, Any]:
    passed_fields = []
    missing_fields = []
    for rule in required:
        field = rule["field"]
        if _evidence_passes(
            context,
            field,
            rule.get("accepted_statuses", VALID_EVIDENCE_STATUSES),
            rule.get("accepted_values"),
        ):
            passed_fields.append(field)
        else:
            missing_fields.append(field)
    return {
        "gate_id": gate_id,
        "version": 1,
        "status": "ready_for_rule_evaluation" if not missing_fields else "information_required",
        "passed_fields": passed_fields,
        "missing_fields": missing_fields,
        "stale_fields": [],
        "conflicting_fields": [],
        "next_action": {
            "type": "human_review" if not missing_fields else "collect_seller_input",
            "label": "Proceed to the rule evaluation." if not missing_fields else "Provide the missing evidence without guessing.",
        },
    }


def evaluate_gates(
    intake: Mapping[str, Any], feasibility: Mapping[str, Any], context: Mapping[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """Evaluate stable gate contracts before strategy rules or agent prose."""

    feasibility_gate = {
        "gate_id": "FEASIBILITY-GATE-001",
        "version": 1,
        "status": "ready_for_rule_evaluation",
        "passed_fields": [
            "monthly_sales_target", "product_price_usd", "target_tacos_percent",
            "ad_sales_share_percent", "benchmark_cpc_usd", "benchmark_cvr_percent",
        ],
        "missing_fields": [],
        "stale_fields": [],
        "conflicting_fields": (
            [] if feasibility["is_feasible_at_benchmark"] else ["benchmark_cvr_percent"]
        ),
        "next_action": {
            "type": "human_review",
            "label": "Resolve the visible feasibility conflict before committing campaign budgets."
            if not feasibility["is_feasible_at_benchmark"]
            else "Feasibility inputs are ready for downstream evidence gates.",
        },
    }
    sb_gate = _evidence_gate(
        "SB-GATE-001",
        [
            {"field": "advertiser_account_status", "accepted_statuses": ["verified"]},
            {"field": "brand_registry_status", "accepted_statuses": ["verified"], "accepted_values": ["enrolled"]},
            {"field": "campaign_goal", "accepted_statuses": ["confirmed"]},
            {"field": "eligible_advertised_asins", "accepted_statuses": ["verified", "external_evidence"]},
        ],
        context,
    )
    sd_gate = _evidence_gate(
        "SD-GATE-001",
        [
            {"field": "display_eligibility_status", "accepted_statuses": ["verified"]},
            {"field": "campaign_goal", "accepted_statuses": ["confirmed"]},
            {"field": "new_product_asin", "accepted_statuses": list(VALID_EVIDENCE_STATUSES)},
            {"field": "old_product_asins", "accepted_statuses": list(VALID_EVIDENCE_STATUSES)},
            {"field": "catalog_relationship", "accepted_statuses": ["confirmed"], "accepted_values": ["complementary", "upgrade_path", "compatible"]},
            {"field": "inventory_health", "accepted_statuses": list(VALID_EVIDENCE_STATUSES)},
            {"field": "contribution_margin", "accepted_statuses": ["confirmed", "external_evidence"]},
        ],
        context,
    )
    return {
        "FEASIBILITY-GATE-001": feasibility_gate,
        "SB-GATE-001": sb_gate,
        "SD-GATE-001": sd_gate,
    }
