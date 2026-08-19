"""
G&C Central Deal and Brokerage Automation Platform
Domain Models, Data Validation & Serialization
"""
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple


def normalize_name(name: str) -> str:
    """Standardizes party/product names for duplicate matching."""
    if not name:
        return ""
    # Remove punctuation, extra whitespace, convert to uppercase
    cleaned = re.sub(r"[^\w\s]", "", name).strip().upper()
    return re.sub(r"\s+", " ", cleaned)


def parse_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    """
    Parses various date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD) into standard ISO YYYY-MM-DD.
    """
    if not date_str or not str(date_str).strip():
        return None
    d_str = str(date_str).strip()

    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(d_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Return as-is if unparseable
    return d_str


def format_iso_to_display(date_iso: Optional[str]) -> str:
    """Formats ISO YYYY-MM-DD date to Indian display format DD/MM/YYYY."""
    if not date_iso or not str(date_iso).strip():
        return ""
    d_str = str(date_iso).strip()
    try:
        if len(d_str) >= 10:
            dt = datetime.strptime(d_str[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
    except Exception:
        pass
    return d_str


def format_inr(amount: Any) -> str:
    """Formats a number into Indian Rupee currency format (e.g., ₹1,80,000.00)."""
    if amount is None:
        return "₹0.00"
    try:
        dec = Decimal(str(amount))
        is_negative = dec < 0
        dec_abs = abs(dec)
        parts = f"{dec_abs:.2f}".split(".")
        integer_part = parts[0]
        decimal_part = parts[1]

        # Indian digit grouping: last 3 digits, then groups of 2
        if len(integer_part) > 3:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            groups = []
            while len(remaining) > 2:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            if remaining:
                groups.insert(0, remaining)
            formatted_int = ",".join(groups) + "," + last_three
        else:
            formatted_int = integer_part

        sign = "-" if is_negative else ""
        return f"{sign}₹{formatted_int}.{decimal_part}"
    except Exception:
        return f"₹{amount}"


def validate_party_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validates party master submission."""
    name = (data.get("name") or "").strip()
    if not name:
        return False, "Party name is mandatory."

    party_type = (data.get("party_type") or "both").lower()
    if party_type not in ("buyer", "seller", "both"):
        return False, "Party type must be 'buyer', 'seller', or 'both'."

    buyer_rate = data.get("default_buyer_brokerage_rate", 0)
    seller_rate = data.get("default_seller_brokerage_rate", 0)
    try:
        if Decimal(str(buyer_rate)) < 0 or Decimal(str(seller_rate)) < 0:
            return False, "Brokerage rates cannot be negative."
    except Exception:
        return False, "Invalid numeric format for brokerage rates."

    return True, None


def validate_product_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validates product master submission."""
    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip().upper()
    if not name or not code:
        return False, "Product name and short code are mandatory."

    gst_pct = data.get("default_gst_pct", 5.0)
    try:
        if Decimal(str(gst_pct)) < 0:
            return False, "GST percentage cannot be negative."
    except Exception:
        return False, "Invalid GST percentage format."

    return True, None


def validate_deal_data(data: Dict[str, Any], is_resale: bool = False) -> Tuple[bool, Optional[str]]:
    """Validates initial deal or resale submission."""
    buyer_id = data.get("buyer_id")
    seller_id = data.get("seller_id")
    product_id = data.get("product_id")

    if not buyer_id:
        return False, "Buyer is required."
    if not seller_id:
        return False, "Seller is required."
    if not product_id:
        return False, "Product is required."

    if str(buyer_id) == str(seller_id):
        allow_self = data.get("allow_same_party", False)
        if not allow_self:
            return False, "Buyer and Seller cannot be identical without explicit authorization."

    # Quantity check
    qty = data.get("quantity_qtl", 0)
    try:
        dec_qty = Decimal(str(qty))
        if dec_qty <= 0:
            return False, "Quantity must be greater than zero."
    except Exception:
        return False, "Invalid quantity numeric value."

    # Rate check
    rate = data.get("rate_per_qtl", data.get("actual_rate_per_qtl", 0))
    try:
        dec_rate = Decimal(str(rate))
        if dec_rate <= 0:
            return False, "Rate per quintal must be greater than zero."
    except Exception:
        return False, "Invalid rate numeric value."

    # Brokerage check
    b_rate = data.get("buyer_brokerage_rate_per_tonne", 0)
    s_rate = data.get("seller_brokerage_rate_per_tonne", 0)
    try:
        if Decimal(str(b_rate)) < 0 or Decimal(str(s_rate)) < 0:
            return False, "Brokerage rate per tonne cannot be negative."
    except Exception:
        return False, "Invalid brokerage rate value."

    # Resale specific check
    if is_resale:
        auth_rate = data.get("authorized_rate_per_qtl", 0)
        try:
            if Decimal(str(auth_rate)) <= 0:
                return False, "Authorized resale rate per quintal is required."
        except Exception:
            return False, "Invalid authorized rate value."

    return True, None
