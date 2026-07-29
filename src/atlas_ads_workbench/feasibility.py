"""Deterministic, explainable Amazon Ads feasibility calculations."""

from typing import Any, Dict, Mapping


def calculate_feasibility(intake: Mapping[str, Any]) -> Dict[str, Any]:
    """Calculate constraints from seller inputs without external data or models."""

    price = float(intake["product_price_usd"])
    monthly_sales = float(intake["monthly_sales_target"])
    tacos = float(intake["target_tacos_percent"]) / 100
    ad_share = float(intake["ad_sales_share_percent"]) / 100
    cpc = float(intake["benchmark_cpc_usd"])
    cvr = float(intake["benchmark_cvr_percent"]) / 100

    monthly_revenue = monthly_sales * price
    monthly_ad_spend = monthly_revenue * tacos
    daily_ad_spend = monthly_ad_spend / 30
    daily_ad_orders = monthly_sales * ad_share / 30
    ad_acos_cap = tacos / ad_share
    required_cvr = cpc / (price * ad_acos_cap)
    required_ad_acos_at_benchmark = cpc / (price * cvr)
    implied_tacos_at_benchmark = required_ad_acos_at_benchmark * ad_share
    max_cpc_at_benchmark = price * ad_acos_cap * cvr
    max_ad_sales_share_at_benchmark = min(1.0, tacos / required_ad_acos_at_benchmark)
    is_feasible = required_cvr <= cvr

    basis = [
        {
            "kind": "seller_input",
            "field": field,
            "value": intake[field],
        }
        for field in (
            "monthly_sales_target",
            "product_price_usd",
            "target_tacos_percent",
            "ad_sales_share_percent",
            "benchmark_cpc_usd",
            "benchmark_cvr_percent",
        )
    ]
    formulae = {
        "monthly_revenue_target_usd": "monthly_sales_target × product_price_usd",
        "monthly_ad_spend_cap_usd": "monthly_revenue_target_usd × target_tacos_percent",
        "daily_ad_spend_cap_usd": "monthly_ad_spend_cap_usd ÷ 30",
        "daily_ad_orders_target": "monthly_sales_target × ad_sales_share_percent ÷ 30",
        "ad_acos_cap_percent": "target_tacos_percent ÷ ad_sales_share_percent",
        "required_cvr_percent": "benchmark_cpc_usd ÷ (product_price_usd × ad_acos_cap)",
    }

    alerts = []
    levers = []
    if not is_feasible:
        alerts.append(
            {
                "kind": "constraint_conflict",
                "message": (
                    "The required conversion rate exceeds the seller assumption "
                    "benchmark. Adjust a visible input before treating this as a plan."
                ),
                "required_cvr_percent": required_cvr * 100,
                "benchmark_cvr_percent": cvr * 100,
            }
        )
        levers = [
            {
                "field": "benchmark_cpc_usd",
                "direction": "lower",
                "threshold": max_cpc_at_benchmark,
                "unit": "USD",
                "basis": "Maximum CPC at the current TACoS, ad-sales share, price, and seller CVR assumption.",
            },
            {
                "field": "target_tacos_percent",
                "direction": "higher",
                "threshold": implied_tacos_at_benchmark * 100,
                "unit": "percent",
                "basis": "Implied total TACoS if the current CPC, ad-sales share, price, and seller CVR assumption hold.",
            },
            {
                "field": "ad_sales_share_percent",
                "direction": "lower",
                "threshold": max_ad_sales_share_at_benchmark * 100,
                "unit": "percent",
                "basis": "Maximum ad-sales share under the current TACoS, CPC, price, and seller CVR assumption.",
            },
        ]

    return {
        "calculation_version": 1,
        "data_source": "seller_input",
        "external_data_used": False,
        "model_calls": 0,
        "basis": basis,
        "formulae": formulae,
        "monthly_revenue_target_usd": monthly_revenue,
        "monthly_ad_spend_cap_usd": monthly_ad_spend,
        "daily_ad_spend_cap_usd": daily_ad_spend,
        "daily_ad_orders_target": daily_ad_orders,
        "ad_acos_cap_percent": ad_acos_cap * 100,
        "required_cvr_percent": required_cvr * 100,
        "benchmark_cvr_percent": cvr * 100,
        "implied_tacos_at_benchmark_percent": implied_tacos_at_benchmark * 100,
        "is_feasible_at_benchmark": is_feasible,
        "alerts": alerts,
        "levers": levers,
    }
