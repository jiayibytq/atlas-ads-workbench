"""Deterministic, explicitly non-executable SP demo reports."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Mapping


CENT = Decimal("0.01")
DEMO_ROWS = (
    {
        "ad_type": "SP",
        "purpose": "探索搜索词",
        "budget_share_percent": 30,
        "target": "demo running socks",
        "target_type": "自动采样",
    },
    {
        "ad_type": "SP",
        "purpose": "验证核心词",
        "budget_share_percent": 45,
        "target": "demo compression socks",
        "target_type": "精准",
    },
    {
        "ad_type": "SP",
        "purpose": "验证关联商品",
        "budget_share_percent": 25,
        "target": "DEMO-ASIN-001",
        "target_type": "商品投放",
    },
)


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _seller_derived_daily_budget(feasibility: Mapping[str, Any]) -> Decimal:
    basis = {
        item["field"]: Decimal(str(item["value"]))
        for item in feasibility.get("basis", [])
        if item.get("field")
        in {"monthly_sales_target", "product_price_usd", "target_tacos_percent"}
    }
    if len(basis) == 3:
        return (
            basis["monthly_sales_target"]
            * basis["product_price_usd"]
            * basis["target_tacos_percent"]
            / Decimal("100")
            / Decimal("30")
        )
    return Decimal(str(feasibility["daily_ad_spend_cap_usd"]))


def build_demo_report(feasibility: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a fixed-data report from the seller-derived total budget."""

    total = _money(_seller_derived_daily_budget(feasibility))
    rows = []
    allocated = Decimal("0.00")
    for index, template in enumerate(DEMO_ROWS):
        if index == len(DEMO_ROWS) - 1:
            budget = total - allocated
        else:
            share = Decimal(str(template["budget_share_percent"])) / Decimal("100")
            budget = _money(total * share)
            allocated += budget
        rows.append(
            {
                **template,
                "daily_budget_usd": float(budget),
                "is_demo": True,
            }
        )

    warnings = []
    is_feasible = bool(feasibility["is_feasible_at_benchmark"])
    if not is_feasible:
        warnings.append(
            "当前输入假设存在可行性冲突；本表仅用于演示流程，不可直接执行。"
        )

    summary = (
        "本次演示将总日预算拆分为三种 SP 任务：自动采样用于收集搜索词信号，"
        "精准投放用于验证核心词，商品投放用于演示关联 ASIN 测试。"
        "预算分配来自固定演示规则，不代表真实市场建议。"
        "正式执行前仍需补充关键词、商品定向和账户资格证据。"
    )
    if not is_feasible:
        summary += "当前输入假设存在可行性冲突，正式决策前必须先调整并复核。"

    return {
        "report_version": 1,
        "report_type": "demo",
        "feasibility_status": (
            "feasible_at_benchmark" if is_feasible else "constraint_conflict"
        ),
        "is_executable": False,
        "data_source": "seller_input_and_fixed_demo_data",
        "external_data_used": False,
        "model_calls": 0,
        "total_daily_budget_usd": float(total),
        "budget_basis": "卖家月销售目标 × 产品售价 × 目标 TACoS ÷ 30",
        "allocation_rule": "demo-report-v1: 30% / 45% / 25%",
        "rows": rows,
        "summary": summary,
        "warnings": warnings,
    }
