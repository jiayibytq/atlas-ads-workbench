"""Deterministic campaign-allocation drafts with visible stage rules."""

from typing import Any, Dict, Mapping


STAGE_SHARES = {
    "launch": (34, 24, 23, 19),
    "growth": (20, 25, 25, 30),
    "mature": (10, 25, 25, 40),
    "clearance": (20, 20, 30, 30),
}

CAMPAIGNS = (
    ("auto-sampling", "自动采样", "Discover search terms and ASIN signals before committing exact budgets."),
    ("manual-broad", "手动广泛探索", "Test controlled discovery queries under a visible spend cap."),
    ("product-targeting", "商品投放", "Compare relevant competing or adjacent products after human review."),
    ("manual-exact", "手动精准验证", "Validate terms that earn a deliberate transfer decision."),
)


def build_campaign_architecture(
    intake: Mapping[str, Any], feasibility: Mapping[str, Any]
) -> Dict[str, Any]:
    """Build a non-executing campaign budget draft from stage rules only."""

    stage = intake["product_stage"]
    shares = STAGE_SHARES[stage]
    daily_budget = float(feasibility["daily_ad_spend_cap_usd"])
    campaigns = []
    for (identifier, name, objective), share in zip(CAMPAIGNS, shares):
        campaigns.append(
            {
                "id": identifier,
                "name": name,
                "objective": objective,
                "budget_share_percent": share,
                "daily_budget_usd": daily_budget * share / 100,
                "basis": (
                    "A deterministic stage rule for %s; it is a budget draft, "
                    "not external market evidence." % stage
                ),
                "adjustment_condition": (
                    "Require human review after new evidence or a change to the frozen input assumptions."
                ),
            }
        )

    feasible = bool(feasibility["is_feasible_at_benchmark"])
    return {
        "architecture_version": 1,
        "data_source": "deterministic_rule",
        "external_data_used": False,
        "model_calls": 0,
        "status": "ready_for_human_review" if feasible else "review_required",
        "review_reason": (
            "The feasibility inputs are internally consistent. Human approval is still required."
            if feasible
            else "Resolve the visible feasibility constraint before treating this allocation as a plan."
        ),
        "stage_rule": stage,
        "daily_budget_usd": daily_budget,
        "campaigns": campaigns,
    }
