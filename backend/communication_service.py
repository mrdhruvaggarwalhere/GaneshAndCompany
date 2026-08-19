"""
G&C Central Deal and Brokerage Automation Platform
Zero-Cost WhatsApp & Email Communication Service
Compliant with Strict Cost Restrictions (wa.me click-to-chat and mailto: URI schemes)
"""
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple, List


# Configurable Communication Adapter Modes
COMM_MODES = {
    "WHATSAPP_CLICK_TO_CHAT": True,   # Active (Zero-Cost)
    "WHATSAPP_BUSINESS_API": False,  # Disabled / Inactive
    "EMAIL_MAILTO": True,            # Active (Zero-Cost)
    "EMAIL_SMTP": False,             # Disabled / Inactive
}


def normalize_indian_phone(phone: Optional[str]) -> str:
    """
    Normalizes phone numbers to standard Indian international format (91XXXXXXXXXX).
    Strips non-digits, removes '+', spaces, hyphens, brackets, leading zeroes.
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return ""
    
    # Remove leading 0 if present (e.g. 09876543210 -> 9876543210)
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    
    # If 10 digits, prepend India code 91
    if len(digits) == 10:
        return f"91{digits}"
    
    # If starts with 91 and has 12 digits, return as is
    if digits.startswith("91") and len(digits) == 12:
        return digits
    
    return digits


def validate_email(email: Optional[str]) -> bool:
    """Validates email format."""
    if not email:
        return False
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(email_pattern, email.strip()))


def format_inr_curr(val: Any) -> str:
    """Formats numeric amount in Indian numbering system."""
    try:
        dec = Decimal(str(val or 0))
        return f"{dec:,.2f}"
    except Exception:
        return "0.00"


def format_date_dmy(date_str: Optional[str]) -> str:
    """Converts ISO date (YYYY-MM-DD) to DD/MM/YYYY."""
    if not date_str:
        return datetime.now().strftime("%d/%m/%Y")
    try:
        if "-" in date_str and len(date_str) >= 10:
            parts = date_str[:10].split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return str(date_str)


def format_qty_str(val: Any) -> str:
    """Formats quantity in clean string format (integer if whole, decimal otherwise)."""
    try:
        dec = Decimal(str(val or 0)).normalize()
        if dec == dec.to_integral():
            return f"{int(dec)}"
        return f"{dec:f}"
    except Exception:
        return str(val)


def generate_communication_draft(
    message_type: str,
    party: Dict[str, Any],
    deal: Optional[Dict[str, Any]] = None,
    chain: Optional[Dict[str, Any]] = None,
    chain_totals: Optional[Dict[str, Any]] = None,
    ledger: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates exact subject and body templates according to strict brokerage privacy standards.
    Internal price-difference profit and counterparty brokerages are NEVER included in client messages.
    """
    options = options or {}
    include_rate = options.get("include_rate", True)
    include_gst = options.get("include_gst", True)
    include_brokerage = options.get("include_brokerage", False)  # Off by default for ordinary confirmations
    include_total = options.get("include_total", True)
    custom_text = options.get("custom_text", "")

    party_name = party.get("name", "Valued Client")
    contact_person = party.get("contact_person") or party_name

    subject = ""
    body = ""

    # 1. Deal Confirmation to Buyer
    if message_type == "deal_confirmation_buyer":
        deal_num = deal.get("deal_number", "DL-NEW") if deal else "DL-NEW"
        deal_date = format_date_dmy(deal.get("deal_date") if deal else None)
        deliv_date = format_date_dmy(deal.get("delivery_date") if deal else None)
        prod = deal.get("product_name") or deal.get("product_code", "Edible Oil") if deal else "Edible Oil"
        qty_qtl = Decimal(str(deal.get("quantity_qtl", 0))) if deal else Decimal("0")
        qty_mt = qty_qtl / Decimal("10")
        qty_qtl_str = format_qty_str(qty_qtl)
        qty_mt_str = format_qty_str(qty_mt)
        seller = deal.get("seller_name", "Supplier") if deal else "Supplier"
        rate = format_inr_curr(deal.get("rate_per_qtl", 0)) if deal else "0.00"
        gst_str = " + GST" if (deal and deal.get("gst_applicable", True)) else ""

        subject = f"G&C Deal Confirmation – {deal_num}"
        body = (
            f"Dear {contact_person},\n\n"
            f"Your deal has been confirmed.\n\n"
            f"Deal ID: {deal_num}\n"
            f"Deal Date: {deal_date}\n"
            f"Product: {prod}\n"
            f"Quantity: {qty_qtl_str} quintals ({qty_mt_str} metric tonnes)\n"
            f"Seller: {seller}\n"
        )
        if include_rate:
            body += f"Rate: ₹{rate}{gst_str} per quintal\n"
        if include_total and deal and deal.get("total_value"):
            body += f"Total Approximate Value: ₹{format_inr_curr(deal.get('total_value'))}\n"
        if include_brokerage and deal and deal.get("buyer_brokerage_amount"):
            body += f"Brokerage Charge: ₹{format_inr_curr(deal.get('buyer_brokerage_amount'))}\n"
        
        body += (
            f"Delivery Date: {deliv_date}\n\n"
            f"Please confirm the above details.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 2. Deal Confirmation to Seller
    elif message_type == "deal_confirmation_seller":
        deal_num = deal.get("deal_number", "DL-NEW") if deal else "DL-NEW"
        deal_date = format_date_dmy(deal.get("deal_date") if deal else None)
        deliv_date = format_date_dmy(deal.get("delivery_date") if deal else None)
        prod = deal.get("product_name") or deal.get("product_code", "Edible Oil") if deal else "Edible Oil"
        qty_qtl = Decimal(str(deal.get("quantity_qtl", 0))) if deal else Decimal("0")
        qty_mt = qty_qtl / Decimal("10")
        qty_qtl_str = format_qty_str(qty_qtl)
        qty_mt_str = format_qty_str(qty_mt)
        buyer = deal.get("buyer_name", "Purchaser") if deal else "Purchaser"
        rate = format_inr_curr(deal.get("rate_per_qtl", 0)) if deal else "0.00"
        gst_str = " + GST" if (deal and deal.get("gst_applicable", True)) else ""

        subject = f"G&C Seller Confirmation – {deal_num}"
        body = (
            f"Dear {contact_person},\n\n"
            f"The following deal has been confirmed.\n\n"
            f"Deal ID: {deal_num}\n"
            f"Deal Date: {deal_date}\n"
            f"Buyer: {buyer}\n"
            f"Product: {prod}\n"
            f"Quantity: {qty_qtl_str} quintals ({qty_mt_str} metric tonnes)\n"
        )
        if include_rate:
            body += f"Rate: ₹{rate}{gst_str} per quintal\n"
        if include_total and deal and deal.get("total_value"):
            body += f"Total Approximate Value: ₹{format_inr_curr(deal.get('total_value'))}\n"
        if include_brokerage and deal and deal.get("seller_brokerage_amount"):
            body += f"Brokerage Charge: ₹{format_inr_curr(deal.get('seller_brokerage_amount'))}\n"

        body += (
            f"Delivery Date: {deliv_date}\n\n"
            f"Please confirm the above details.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 3. Final Commercial Direct Billing Instruction
    elif message_type == "final_billing_instruction":
        chain_code = chain.get("chain_code", "CHN-NEW") if chain else "CHN-NEW"
        prod = chain.get("product_name") or chain.get("product_code", "MUSTARD OIL") if chain else "MUSTARD OIL"
        orig_seller = (chain_totals.get("original_bill_seller_name") if chain_totals else None) or chain.get("original_bill_seller_name") or party_name
        final_buyer = (chain_totals.get("final_bill_buyer_name") if chain_totals else None) or chain.get("final_bill_buyer_name") or "Final Buyer"
        final_rate = format_inr_curr((chain_totals.get("final_billing_rate") if chain_totals else None) or chain.get("final_billing_rate", 0))
        qty_qtl = Decimal(str((chain_totals.get("final_quantity_qtl") if chain_totals else None) or chain.get("remaining_quantity_qtl") or chain.get("initial_quantity_qtl", 0)))
        deliv_date = format_date_dmy(datetime.now().strftime("%Y-%m-%d"))

        subject = f"G&C Direct Billing Instruction – {chain_code}"
        body = (
            f"Dear {orig_seller},\n\n"
            f"Please issue the direct bill according to the following details:\n\n"
            f"Deal Chain ID: {chain_code}\n"
            f"Bill From: {orig_seller}\n"
            f"Bill To: {final_buyer}\n"
            f"Product: {prod}\n"
            f"Quantity: {format_qty_str(qty_qtl)} quintals\n"
            f"Rate: ₹{final_rate} + GST per quintal\n"
            f"Delivery/Billing Date: {deliv_date}\n\n"
            f"Please confirm after the bill has been prepared.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 4. Delivery Reminder
    elif message_type == "delivery_reminder":
        deal_num = deal.get("deal_number", "DL-NEW") if deal else "DL-NEW"
        deliv_date = format_date_dmy(deal.get("delivery_date") if deal else None)
        prod = deal.get("product_name") or deal.get("product_code", "Edible Oil") if deal else "Edible Oil"
        qty_qtl = Decimal(str(deal.get("quantity_qtl", 0))) if deal else Decimal("0")
        buyer = deal.get("buyer_name", "Buyer") if deal else "Buyer"
        seller = deal.get("seller_name", "Seller") if deal else "Seller"

        subject = f"G&C Delivery Reminder – {deal_num}"
        body = (
            f"Dear {contact_person},\n\n"
            f"This is a reminder regarding the following delivery:\n\n"
            f"Deal ID: {deal_num}\n"
            f"Product: {prod}\n"
            f"Quantity: {format_qty_str(qty_qtl)} quintals\n"
            f"Delivery Date: {deliv_date}\n"
            f"Buyer: {buyer}\n"
            f"Seller: {seller}\n\n"
            f"Please share the current delivery status.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 5. Rate Confirmation
    elif message_type == "rate_confirmation":
        deal_num = deal.get("deal_number", "DL-NEW") if deal else "DL-NEW"
        prod = deal.get("product_name") or deal.get("product_code", "Edible Oil") if deal else "Edible Oil"
        qty_qtl = Decimal(str(deal.get("quantity_qtl", 0))) if deal else Decimal("0")
        rate = format_inr_curr(deal.get("rate_per_qtl", 0)) if deal else "0.00"

        subject = f"G&C Rate Confirmation – {deal_num}"
        body = (
            f"Dear {contact_person},\n\n"
            f"This is to confirm the agreed rate for the following transaction:\n\n"
            f"Deal ID: {deal_num}\n"
            f"Product: {prod}\n"
            f"Quantity: {format_qty_str(qty_qtl)} quintals\n"
            f"Agreed Rate: ₹{rate} + GST per quintal\n\n"
            f"Please confirm your acceptance.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 6. Deal Amendment Notice
    elif message_type == "deal_amendment":
        deal_num = deal.get("deal_number", "DL-NEW") if deal else "DL-NEW"
        prod = deal.get("product_name") or deal.get("product_code", "Edible Oil") if deal else "Edible Oil"
        qty_qtl = Decimal(str(deal.get("quantity_qtl", 0))) if deal else Decimal("0")
        rate = format_inr_curr(deal.get("rate_per_qtl", 0)) if deal else "0.00"
        deliv_date = format_date_dmy(deal.get("delivery_date") if deal else None)
        notes = deal.get("notes") or custom_text or "Details revised upon mutual agreement."

        subject = f"G&C Deal Amendment – {deal_num}"
        body = (
            f"Dear {contact_person},\n\n"
            f"Please note that the following deal has been amended:\n\n"
            f"Deal ID: {deal_num}\n"
            f"Product: {prod}\n"
            f"Quantity: {format_qty_str(qty_qtl)} quintals\n"
            f"Rate: ₹{rate} + GST per quintal\n"
            f"Delivery Date: {deliv_date}\n"
            f"Amendment Details: {notes}\n\n"
            f"Please confirm the updated terms.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 7. Deal Cancellation Notice
    elif message_type == "deal_cancellation":
        deal_num = deal.get("deal_number", "DL-NEW") if deal else "DL-NEW"
        prod = deal.get("product_name") or deal.get("product_code", "Edible Oil") if deal else "Edible Oil"
        qty_qtl = Decimal(str(deal.get("quantity_qtl", 0))) if deal else Decimal("0")
        reason = (deal.get("cancellation_reason") if deal else None) or custom_text or "Cancelled upon party request."

        subject = f"G&C Deal Cancellation – {deal_num}"
        body = (
            f"Dear {contact_person},\n\n"
            f"Please note that the following deal has been cancelled:\n\n"
            f"Deal ID: {deal_num}\n"
            f"Product: {prod}\n"
            f"Quantity: {format_qty_str(qty_qtl)} quintals\n"
            f"Cancellation Reason: {reason}\n\n"
            f"Please update your records accordingly.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 8. Brokerage Statement
    elif message_type == "brokerage_statement":
        date_range = options.get("date_range") or f"FY {datetime.now().strftime('%Y')}"
        s = ledger.get("summary", {}) if ledger else {}
        open_bal = format_inr_curr(s.get("opening_balance", 0))
        buyer_brok = format_inr_curr(s.get("buyer_side_brokerage", s.get("total_brokerage_charged", 0)))
        seller_brok = format_inr_curr(s.get("seller_side_brokerage", 0))
        total_paid = format_inr_curr(s.get("total_brokerage_paid", 0))
        balance = format_inr_curr(s.get("outstanding_balance", 0))

        subject = f"G&C Brokerage Statement – {date_range}"
        body = (
            f"Dear {contact_person},\n\n"
            f"Your brokerage statement for {date_range} is as follows:\n\n"
            f"Opening Balance: ₹{open_bal}\n"
            f"Buyer-Side Brokerage: ₹{buyer_brok}\n"
            f"Seller-Side Brokerage: ₹{seller_brok}\n"
            f"Payments/Adjustments: ₹{total_paid}\n"
            f"Outstanding Balance: ₹{balance}\n\n"
            f"Please contact us if any clarification is required.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 9. Brokerage Payment Reminder
    elif message_type == "brokerage_payment_reminder":
        s = ledger.get("summary", {}) if ledger else {}
        balance = format_inr_curr(s.get("outstanding_balance", 0))

        subject = f"G&C Payment Reminder – {party_name}"
        body = (
            f"Dear {contact_person},\n\n"
            f"This is a reminder that an outstanding brokerage balance of ₹{balance} is pending for settlement.\n\n"
            f"Outstanding Balance: ₹{balance}\n\n"
            f"Please arrange for the settlement at your earliest convenience.\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # 10. Custom Message
    else:
        subject = f"G&C Commodity Notice – {party_name}"
        body = (
            f"Dear {contact_person},\n\n"
            f"{custom_text or 'Please find the deal communication update below.'}\n\n"
            f"Regards,\n"
            f"G&C"
        )

    # Prepare Contact Candidates
    whatsapp_candidates = []
    if party.get("whatsapp_primary"):
        whatsapp_candidates.append({
            "type": "primary",
            "label": f"Primary WhatsApp ({party['whatsapp_primary']})",
            "value": normalize_indian_phone(party["whatsapp_primary"])
        })
    elif party.get("phone"):
        whatsapp_candidates.append({
            "type": "primary",
            "label": f"Primary Phone ({party['phone']})",
            "value": normalize_indian_phone(party["phone"])
        })
    
    if party.get("whatsapp_secondary"):
        whatsapp_candidates.append({
            "type": "secondary",
            "label": f"Secondary WhatsApp ({party['whatsapp_secondary']})",
            "value": normalize_indian_phone(party["whatsapp_secondary"])
        })

    email_candidates = []
    if party.get("email_primary"):
        email_candidates.append({
            "type": "primary",
            "label": f"Primary Email ({party['email_primary']})",
            "value": party["email_primary"].strip()
        })
    elif party.get("email"):
        email_candidates.append({
            "type": "primary",
            "label": f"Primary Email ({party['email']})",
            "value": party["email"].strip()
        })

    if party.get("email_secondary"):
        email_candidates.append({
            "type": "secondary",
            "label": f"Secondary Email ({party['email_secondary']})",
            "value": party["email_secondary"].strip()
        })

    preferred_method = party.get("preferred_comm_method", "both")

    return {
        "message_type": message_type,
        "party_id": party.get("id"),
        "party_name": party_name,
        "contact_person": contact_person,
        "subject": subject,
        "body": body,
        "whatsapp_candidates": whatsapp_candidates,
        "email_candidates": email_candidates,
        "preferred_method": preferred_method,
        "whatsapp_enabled": bool(party.get("whatsapp_enabled", 1)),
        "email_enabled": bool(party.get("email_enabled", 1)),
        "is_financial_statement": message_type in ("brokerage_statement", "brokerage_payment_reminder"),
        "active_modes": COMM_MODES
    }
