"""
G&C Central Deal and Brokerage Automation Platform
Exact Decimal Calculation Engine
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, Any, Optional, Tuple, List

# Standard constants
QUINTALS_PER_TONNE = Decimal("10")
DEFAULT_DECIMAL_PLACES = Decimal("0.01")
RATE_DECIMAL_PLACES = Decimal("0.01")
QTY_DECIMAL_PLACES = Decimal("0.001")


def to_decimal(value: Any, default: str = "0") -> Decimal:
    """Safely converts any numeric input to Decimal without floating-point errors."""
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        # Convert to string first to prevent float representation imprecision
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return Decimal(default)


def round_currency(value: Decimal) -> Decimal:
    """Rounds currency amounts to 2 decimal places using standard ROUND_HALF_UP."""
    return value.quantize(DEFAULT_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def round_quantity(value: Decimal) -> Decimal:
    """Rounds quantity to 3 decimal places for fractional tonnes."""
    return value.quantize(QTY_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def convert_quintals_to_tonnes(quantity_in_quintals: Decimal) -> Decimal:
    """
    quantity_in_tonnes = quantity_in_quintals / 10
    Example: 320 quintals = 32 metric tonnes
    """
    q = to_decimal(quantity_in_quintals)
    return round_quantity(q / QUINTALS_PER_TONNE)


def convert_tonnes_to_quintals(quantity_in_tonnes: Decimal) -> Decimal:
    """
    quantity_in_quintals = quantity_in_tonnes * 10
    Example: 32 metric tonnes = 320 quintals
    """
    t = to_decimal(quantity_in_tonnes)
    return round_quantity(t * QUINTALS_PER_TONNE)


def calculate_price_difference(actual_sale_rate: Decimal, party_authorized_rate: Decimal) -> Decimal:
    """
    price_difference_per_quintal = actual_sale_rate_per_quintal - party_authorized_rate_per_quintal
    Can be positive (profit), zero, or negative (loss).
    """
    actual = to_decimal(actual_sale_rate)
    auth = to_decimal(party_authorized_rate)
    return actual - auth


def calculate_price_difference_profit(
    quantity_in_quintals: Decimal,
    actual_sale_rate: Decimal,
    party_authorized_rate: Decimal
) -> Tuple[Decimal, Decimal]:
    """
    Calculates rate difference per quintal and total price-difference profit.
    price_difference_profit = price_difference_per_quintal * quantity_in_quintals
    Returns: (diff_per_quintal, total_profit)
    """
    qty_qtl = to_decimal(quantity_in_quintals)
    diff_per_qtl = calculate_price_difference(actual_sale_rate, party_authorized_rate)
    total_profit = round_currency(diff_per_qtl * qty_qtl)
    return diff_per_qtl, total_profit


def calculate_buyer_brokerage(
    quantity_in_tonnes: Decimal,
    buyer_brokerage_rate_per_tonne: Decimal
) -> Decimal:
    """
    buyer_brokerage = quantity_in_tonnes * buyer_brokerage_rate_per_tonne
    """
    tonnes = to_decimal(quantity_in_tonnes)
    rate = to_decimal(buyer_brokerage_rate_per_tonne)
    return round_currency(tonnes * rate)


def calculate_seller_brokerage(
    quantity_in_tonnes: Decimal,
    seller_brokerage_rate_per_tonne: Decimal
) -> Decimal:
    """
    seller_brokerage = quantity_in_tonnes * seller_brokerage_rate_per_tonne
    """
    tonnes = to_decimal(quantity_in_tonnes)
    rate = to_decimal(seller_brokerage_rate_per_tonne)
    return round_currency(tonnes * rate)


def calculate_deal_brokerage(
    quantity_in_tonnes: Decimal,
    buyer_brokerage_rate_per_tonne: Decimal,
    seller_brokerage_rate_per_tonne: Decimal
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculates buyer, seller, and combined deal brokerage.
    Returns: (buyer_brokerage, seller_brokerage, total_deal_brokerage)
    """
    b_brok = calculate_buyer_brokerage(quantity_in_tonnes, buyer_brokerage_rate_per_tonne)
    s_brok = calculate_seller_brokerage(quantity_in_tonnes, seller_brokerage_rate_per_tonne)
    total = b_brok + s_brok
    return b_brok, s_brok, total


def calculate_gst_breakdown(
    rate_per_quintal: Decimal,
    quantity_in_quintals: Decimal,
    gst_applicable: bool,
    gst_pct: Decimal,
    is_rate_gst_inclusive: bool = False
) -> Dict[str, Decimal]:
    """
    Calculates GST breakdown for commercial transactions.
    """
    rate = to_decimal(rate_per_quintal)
    qty = to_decimal(quantity_in_quintals)
    gst_rate = to_decimal(gst_pct) if gst_applicable else Decimal("0")

    if not gst_applicable or gst_rate == Decimal("0"):
        taxable_rate = rate
        taxable_value = round_currency(taxable_rate * qty)
        gst_amount = Decimal("0.00")
        total_value = taxable_value
    elif is_rate_gst_inclusive:
        # Rate includes GST: taxable = rate / (1 + gst_rate/100)
        taxable_rate = rate / (Decimal("1") + (gst_rate / Decimal("100")))
        taxable_value = round_currency(taxable_rate * qty)
        total_value = round_currency(rate * qty)
        gst_amount = total_value - taxable_value
    else:
        # Rate is + GST
        taxable_rate = rate
        taxable_value = round_currency(taxable_rate * qty)
        gst_amount = round_currency(taxable_value * (gst_rate / Decimal("100")))
        total_value = taxable_value + gst_amount

    return {
        "taxable_rate_per_quintal": taxable_rate,
        "taxable_value": taxable_value,
        "gst_percentage": gst_rate,
        "gst_amount": gst_amount,
        "total_value": total_value,
    }


def compute_deal_summary(deal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete calculation pipeline for a single deal or resale link.
    """
    # Quantity handling
    qty_qtl = to_decimal(deal_data.get("quantity_qtl", 0))
    if qty_qtl == 0 and "quantity_tonnes" in deal_data:
        qty_tonnes = to_decimal(deal_data.get("quantity_tonnes", 0))
        qty_qtl = convert_tonnes_to_quintals(qty_tonnes)
    else:
        qty_tonnes = convert_quintals_to_tonnes(qty_qtl)

    rate_qtl = to_decimal(deal_data.get("rate_per_qtl", 0))
    gst_app = bool(deal_data.get("gst_applicable", True))
    gst_pct = to_decimal(deal_data.get("gst_pct", 5))
    is_inclusive = bool(deal_data.get("is_rate_gst_inclusive", False))

    # Brokerage calculations
    buyer_brok_rate = to_decimal(deal_data.get("buyer_brokerage_rate_per_tonne", 0))
    seller_brok_rate = to_decimal(deal_data.get("seller_brokerage_rate_per_tonne", 0))

    b_brok, s_brok, total_brok = calculate_deal_brokerage(qty_tonnes, buyer_brok_rate, seller_brok_rate)

    # Price difference calculation (if it's a resale link with authorized rate)
    auth_rate = to_decimal(deal_data.get("authorized_rate_per_qtl", 0))
    actual_rate = to_decimal(deal_data.get("actual_rate_per_qtl", rate_qtl))

    if auth_rate > 0:
        diff_per_qtl, price_diff_profit = calculate_price_difference_profit(qty_qtl, actual_rate, auth_rate)
    else:
        diff_per_qtl = Decimal("0.00")
        price_diff_profit = Decimal("0.00")

    gst_info = calculate_gst_breakdown(rate_qtl, qty_qtl, gst_app, gst_pct, is_inclusive)
    total_deal_earning = price_diff_profit + total_brok

    return {
        "quantity_qtl": qty_qtl,
        "quantity_tonnes": qty_tonnes,
        "rate_per_qtl": rate_qtl,
        "authorized_rate_per_qtl": auth_rate,
        "actual_rate_per_qtl": actual_rate,
        "price_diff_per_qtl": diff_per_qtl,
        "price_diff_profit": price_diff_profit,
        "buyer_brokerage_rate_per_tonne": buyer_brok_rate,
        "buyer_brokerage_amount": b_brok,
        "seller_brokerage_rate_per_tonne": seller_brok_rate,
        "seller_brokerage_amount": s_brok,
        "total_brokerage": total_brok,
        "total_deal_earning": total_deal_earning,
        "taxable_value": gst_info["taxable_value"],
        "gst_amount": gst_info["gst_amount"],
        "total_value": gst_info["total_value"],
    }


def compute_chain_totals(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes aggregated figures across an entire deal chain.
    - Excludes cancelled deals.
    - Determines Original Bill Seller and Final Bill Buyer.
    - Sums price-difference profit and brokerage.
    """
    active_deals = [d for d in deals if d.get("status") != "cancelled"]

    if not active_deals:
        return {
            "total_deals": 0,
            "total_price_diff_profit": Decimal("0.00"),
            "total_buyer_brokerage": Decimal("0.00"),
            "total_seller_brokerage": Decimal("0.00"),
            "total_brokerage": Decimal("0.00"),
            "total_chain_earning": Decimal("0.00"),
            "original_bill_seller_id": None,
            "final_bill_buyer_id": None,
            "final_billing_rate": Decimal("0.00"),
            "final_quantity_qtl": Decimal("0.00"),
            "direct_billing_instruction": "No active deals in chain",
        }

    # Sort chronologically by deal_date or creation sequence
    active_deals_sorted = sorted(active_deals, key=lambda x: (x.get("deal_date", ""), x.get("id", 0)))

    total_price_diff_profit = Decimal("0.00")
    total_buyer_brokerage = Decimal("0.00")
    total_seller_brokerage = Decimal("0.00")

    for d in active_deals_sorted:
        total_price_diff_profit += to_decimal(d.get("price_diff_profit", 0))
        total_buyer_brokerage += to_decimal(d.get("buyer_brokerage_amount", 0))
        total_seller_brokerage += to_decimal(d.get("seller_brokerage_amount", 0))

    total_brokerage = total_buyer_brokerage + total_seller_brokerage
    total_chain_earning = total_price_diff_profit + total_brokerage

    first_deal = active_deals_sorted[0]
    last_deal = active_deals_sorted[-1]

    # The buyer's name of the Root Lot Purchase (Link #1) issues the final direct commercial bill to the Final Buyer
    original_bill_seller_id = first_deal.get("buyer_id")
    original_bill_seller_name = first_deal.get("buyer_name", "Root Lot Buyer")
    final_bill_buyer_id = last_deal.get("buyer_id")
    final_bill_buyer_name = last_deal.get("buyer_name", "Final Buyer")
    final_billing_rate = to_decimal(last_deal.get("rate_per_qtl", last_deal.get("actual_rate_per_qtl", 0)))
    final_quantity_qtl = to_decimal(last_deal.get("quantity_qtl", first_deal.get("quantity_qtl", 0)))
    product_name = last_deal.get("product_name", first_deal.get("product_name", "Product"))
    gst_treatment = "+ GST" if last_deal.get("gst_applicable", True) else "(GST Exempt/Inclusive)"

    instruction = (
        f"{original_bill_seller_name} will issue a direct bill to "
        f"{final_bill_buyer_name} for {final_quantity_qtl:f} quintals of "
        f"{product_name} at ₹{final_billing_rate:,.2f} {gst_treatment} per quintal."
    )

    party_profit_breakdown = []
    for idx, d in enumerate(active_deals_sorted):
        profit = to_decimal(d.get("price_diff_profit", 0))
        if profit > 0 or d.get("authorized_rate_per_qtl", 0) > 0:
            party_profit_breakdown.append({
                "link_index": idx + 1,
                "deal_id": d.get("id"),
                "deal_number": d.get("deal_number"),
                "deal_date": d.get("deal_date"),
                "payer_party_id": d.get("buyer_id"),
                "payer_party_name": d.get("buyer_name", "Buyer"),
                "instructing_party_id": d.get("seller_id"),
                "instructing_party_name": d.get("seller_name", "Seller"),
                "authorized_rate": to_decimal(d.get("authorized_rate_per_qtl", 0)),
                "actual_rate": to_decimal(d.get("actual_rate_per_qtl", d.get("rate_per_qtl", 0))),
                "diff_per_qtl": to_decimal(d.get("price_diff_per_qtl", 0)),
                "quantity_qtl": to_decimal(d.get("quantity_qtl", 0)),
                "profit_amount": profit
            })

    return {
        "total_deals": len(active_deals_sorted),
        "total_price_diff_profit": total_price_diff_profit,
        "total_buyer_brokerage": total_buyer_brokerage,
        "total_seller_brokerage": total_seller_brokerage,
        "total_brokerage": total_brokerage,
        "total_chain_earning": total_chain_earning,
        "original_bill_seller_id": original_bill_seller_id,
        "original_bill_seller_name": original_bill_seller_name,
        "final_bill_buyer_id": final_bill_buyer_id,
        "final_bill_buyer_name": final_bill_buyer_name,
        "final_billing_rate": final_billing_rate,
        "final_quantity_qtl": final_quantity_qtl,
        "product_name": product_name,
        "direct_billing_instruction": instruction,
        "party_profit_breakdown": party_profit_breakdown,
    }
