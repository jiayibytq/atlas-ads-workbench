"""Versioned evidence gates that decide whether a rule may be evaluated."""

from typing import Any, Dict, Mapping, Sequence


VALID_EVIDENCE_STATUSES = {"confirmed", "verified", "external_evidence"}
GATE_VERSIONS = {
    "FEASIBILITY-GATE-001": 2,
    "SB-GATE-001": 2,
    "SD-GATE-001": 3,
    "CAMPAIGN-ARCHITECTURE-GATE-001": 1,
}

SB_REQUIRED_EVIDENCE = [
    {"field": "advertiser_account_status", "accepted_statuses": ["verified"]},
    {"field": "brand_registry_status", "accepted_statuses": ["verified"], "accepted_values": ["enrolled"]},
    {"field": "campaign_goal", "accepted_statuses": ["confirmed"]},
    {"field": "eligible_advertised_asins", "accepted_statuses": ["verified", "external_evidence"]},
]

SD_REQUIRED_EVIDENCE = [
    {"field": "display_eligibility_status", "accepted_statuses": ["verified"]},
    {"field": "campaign_goal", "accepted_statuses": ["confirmed"]},
    {"field": "new_product_asin", "accepted_statuses": list(VALID_EVIDENCE_STATUSES)},
    {"field": "inventory_health", "accepted_statuses": list(VALID_EVIDENCE_STATUSES)},
]

SD_CROSS_SELL_REQUIRED_EVIDENCE = [
    {"field": "old_product_asins", "accepted_statuses": list(VALID_EVIDENCE_STATUSES)},
    {"field": "catalog_relationship", "accepted_statuses": ["confirmed"], "accepted_values": ["complementary", "upgrade_path", "compatible"]},
    {"field": "contribution_margin", "accepted_statuses": ["confirmed", "external_evidence"]},
]


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
    missing_external = [
        rule["field"]
        for rule in required
        if "confirmed" not in rule.get("accepted_statuses", [])
        and rule["field"] in missing_fields
    ]
    missing_seller_input = [
        field for field in missing_fields if field not in missing_external
    ]
    status = "verification_required" if missing_external else "information_required"
    seller_status = "等待外部验证" if missing_external else "待补充资料"
    if missing_external and missing_seller_input:
        next_action = {
            "type": "collect_seller_input_and_external_evidence",
            "label": "Provide seller-confirmed inputs and authorized external evidence without guessing.",
        }
    elif missing_external:
        next_action = {
            "type": "collect_external_evidence",
            "label": "Provide the missing authorized external evidence without guessing.",
        }
    elif missing_seller_input:
        next_action = {
            "type": "collect_seller_input",
            "label": "Provide the missing seller-confirmed information without guessing.",
        }
    else:
        next_action = {"type": "human_review", "label": "Proceed to the rule evaluation."}
    return {
        "gate_id": gate_id,
        "version": GATE_VERSIONS[gate_id],
        "applicable": True,
        "status": "ready_for_rule_evaluation" if not missing_fields else status,
        "seller_status": "资料已齐全" if not missing_fields else seller_status,
        "seller_message": (
            "资料已达到规则评估条件。"
            if not missing_fields
            else "只补充已选择广告类型所需的资料；系统不会猜测缺失证据。"
        ),
        "passed_fields": passed_fields,
        "missing_fields": missing_fields,
        "missing_seller_input_fields": missing_seller_input,
        "missing_external_verification_fields": missing_external,
        "stale_fields": [],
        "conflicting_fields": [],
        "next_action": next_action,
    }


def _not_applicable_gate(gate_id: str) -> Dict[str, Any]:
    return {
        "gate_id": gate_id,
        "version": GATE_VERSIONS[gate_id],
        "applicable": False,
        "status": "not_applicable",
        "seller_status": "未选择",
        "seller_message": "你没有选择此广告类型，因此本次无需补充资料。",
        "passed_fields": [],
        "missing_fields": [],
        "stale_fields": [],
        "conflicting_fields": [],
        "next_action": {"type": "none", "label": "No action required."},
    }


def evaluate_gates(
    intake: Mapping[str, Any],
    feasibility: Mapping[str, Any],
    context: Mapping[str, Any],
    selected_ad_modules: Sequence[str] = (),
) -> Dict[str, Dict[str, Any]]:
    """Evaluate stable gate contracts before strategy rules or agent prose."""

    has_conflict = not feasibility["is_feasible_at_benchmark"]
    feasibility_gate = {
        "gate_id": "FEASIBILITY-GATE-001",
        "version": GATE_VERSIONS["FEASIBILITY-GATE-001"],
        "applicable": True,
        "status": "constraint_conflict" if has_conflict else "ready_for_rule_evaluation",
        "seller_status": "存在数值冲突" if has_conflict else "目标可行",
        "seller_message": (
            "预算可以计算，但当前 CPC、CVR、TACoS 与广告销售占比不能同时满足。"
            if has_conflict
            else "基础信息完整，当前假设下未检测到数值冲突。"
        ),
        "passed_fields": [
            "monthly_sales_target", "product_price_usd", "target_tacos_percent",
            "ad_sales_share_percent", "benchmark_cpc_usd", "benchmark_cvr_percent",
        ],
        "missing_fields": [],
        "stale_fields": [],
        "conflicting_fields": (
            [] if not has_conflict else ["benchmark_cvr_percent"]
        ),
        "next_action": {
            "type": "human_review",
            "label": "Resolve the visible feasibility conflict before committing campaign budgets."
            if has_conflict
            else "Feasibility inputs are ready for downstream evidence gates.",
        },
    }
    selected = set(selected_ad_modules)
    sb_gate = (
        _evidence_gate("SB-GATE-001", SB_REQUIRED_EVIDENCE, context)
        if "sb" in selected
        else _not_applicable_gate("SB-GATE-001")
    )
    sd_gate = (
        _evidence_gate(
            "SD-GATE-001",
            SD_REQUIRED_EVIDENCE
            + (SD_CROSS_SELL_REQUIRED_EVIDENCE if "sd_cross_sell" in selected else []),
            context,
        )
        if selected.intersection({"sd", "sd_cross_sell"})
        else _not_applicable_gate("SD-GATE-001")
    )
    return {
        "FEASIBILITY-GATE-001": feasibility_gate,
        "SB-GATE-001": sb_gate,
        "SD-GATE-001": sd_gate,
    }
