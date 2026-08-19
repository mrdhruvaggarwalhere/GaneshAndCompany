"""
G&C Central Deal and Brokerage Automation Platform
Future BUSY Accounting Integration Adapter & Intermediate Voucher Builder
"""
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from database import get_db, row_to_dict, rows_to_dict_list
from calculations import to_decimal


class BusyAccountingAdapter:
    """
    Adapter layer for BUSY Accounting Software integration.
    Generates standard intermediate XML and JSON payloads for:
    1. Direct Sales Invoice (Original Bill Seller -> Final Bill Buyer)
    2. Brokerage Commission Journal Vouchers
    """

    @staticmethod
    def get_party_mapping(party_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM busy_mappings WHERE entity_type = 'party' AND local_id = ?", (party_id,)).fetchone()
            return row_to_dict(row)

    @staticmethod
    def get_product_mapping(product_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM busy_mappings WHERE entity_type = 'product' AND local_id = ?", (product_id,)).fetchone()
            return row_to_dict(row)

    @staticmethod
    def generate_direct_sales_voucher(chain_id: int) -> Dict[str, Any]:
        """
        Generates standard intermediate BUSY Sales Voucher for official direct billing.
        Safety Invariant: Internal intermediate deals are strictly filtered out.
        """
        with get_db() as conn:
            chain = row_to_dict(conn.execute("SELECT * FROM deal_chains WHERE id = ?", (chain_id,)).fetchone())
            if not chain:
                raise ValueError(f"Deal chain {chain_id} not found.")

            if chain["status"] not in ("ready_for_billing", "billed"):
                raise ValueError("Only completed/ready chains with approved direct billing instructions can be exported to BUSY.")

            seller = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (chain["original_bill_seller_id"],)).fetchone())
            buyer = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (chain["final_bill_buyer_id"],)).fetchone())
            product = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (chain["product_id"],)).fetchone())

            if not seller or not buyer:
                raise ValueError("Original Bill Seller and Final Bill Buyer must be resolved before generating direct invoice voucher.")

            qty_qtl = to_decimal(chain["remaining_quantity_qtl"] or chain["initial_quantity_qtl"])
            rate_qtl = to_decimal(chain["final_billing_rate"])
            taxable_amt = qty_qtl * rate_qtl
            gst_pct = to_decimal(product.get("default_gst_pct", 5))
            gst_amt = taxable_amt * (gst_pct / Decimal("100"))
            total_amt = taxable_amt + gst_amt

            voucher_data = {
                "voucher_type": "Sales",
                "voucher_series": "MAIN",
                "voucher_date": datetime.now().strftime("%d-%m-%Y"),
                "chain_code": chain["chain_code"],
                "seller_party": {
                    "local_id": seller["id"],
                    "name": seller["name"],
                    "busy_ledger_id": seller.get("busy_ledger_id") or f"BUSY_LEDGER_{seller['id']}",
                    "gstin": seller.get("gstin")
                },
                "buyer_party": {
                    "local_id": buyer["id"],
                    "name": buyer["name"],
                    "busy_ledger_id": buyer.get("busy_ledger_id") or f"BUSY_LEDGER_{buyer['id']}",
                    "gstin": buyer.get("gstin")
                },
                "item_details": [{
                    "local_id": product["id"],
                    "item_name": product["name"],
                    "busy_item_id": product.get("busy_item_id") or f"BUSY_ITEM_{product['id']}",
                    "quantity_qtl": float(qty_qtl),
                    "quantity_tonnes": float(qty_qtl / Decimal("10")),
                    "rate_per_qtl": float(rate_qtl),
                    "unit": "QTL",
                    "hsn": product.get("hsn_sac", "1514"),
                    "taxable_amount": float(taxable_amt),
                    "gst_rate": float(gst_pct),
                    "gst_amount": float(gst_amt),
                    "total_amount": float(total_amt)
                }],
                "official_note": f"Direct Invoice as per broker deal chain {chain['chain_code']}"
            }

            # Generate Standard BUSY XML representation
            root = ET.Element("BUSY_VOUCHER")
            ET.SubElement(root, "VchType").text = "Sales"
            ET.SubElement(root, "VchSeries").text = "MAIN"
            ET.SubElement(root, "VchDate").text = voucher_data["voucher_date"]
            ET.SubElement(root, "BillNo").text = chain["chain_code"]

            party_elem = ET.SubElement(root, "Party")
            ET.SubElement(party_elem, "Name").text = buyer["name"]
            ET.SubElement(party_elem, "BusyLedgerId").text = voucher_data["buyer_party"]["busy_ledger_id"]

            seller_elem = ET.SubElement(root, "OriginalSeller")
            ET.SubElement(seller_elem, "Name").text = seller["name"]
            ET.SubElement(seller_elem, "BusyLedgerId").text = voucher_data["seller_party"]["busy_ledger_id"]

            items_elem = ET.SubElement(root, "Items")
            item_node = ET.SubElement(items_elem, "Item")
            ET.SubElement(item_node, "ItemName").text = product["name"]
            ET.SubElement(item_node, "BusyItemId").text = voucher_data["item_details"][0]["busy_item_id"]
            ET.SubElement(item_node, "Qty").text = str(float(qty_qtl))
            ET.SubElement(item_node, "Unit").text = "QTL"
            ET.SubElement(item_node, "Rate").text = str(float(rate_qtl))
            ET.SubElement(item_node, "TaxableAmt").text = str(float(taxable_amt))
            ET.SubElement(item_node, "GSTAmt").text = str(float(gst_amt))
            ET.SubElement(item_node, "TotalAmt").text = str(float(total_amt))

            xml_raw = ET.tostring(root, encoding="utf-8")
            parsed = minidom.parseString(xml_raw)
            pretty_xml = parsed.toprettyxml(indent="  ")

            return {
                "json_payload": voucher_data,
                "xml_payload": pretty_xml
            }

    @staticmethod
    def generate_brokerage_journal_voucher(deal_id: int) -> Dict[str, Any]:
        """
        Generates BUSY Journal Voucher for Brokerage Income Receivable.
        Debit Party (Buyer/Seller) -> Credit Brokerage Income Account.
        """
        with get_db() as conn:
            deal = row_to_dict(conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone())
            if not deal:
                raise ValueError(f"Deal {deal_id} not found.")

            buyer = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (deal["buyer_id"],)).fetchone())
            seller = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (deal["seller_id"],)).fetchone())

            b_brok = float(deal.get("buyer_brokerage_amount", 0))
            s_brok = float(deal.get("seller_brokerage_amount", 0))
            total_brok = b_brok + s_brok

            entries = []
            if b_brok > 0:
                entries.append({
                    "account_name": buyer["name"],
                    "busy_ledger_id": buyer.get("busy_ledger_id") or f"BUSY_PARTY_{buyer['id']}",
                    "debit": b_brok,
                    "credit": 0.0,
                    "narration": f"Buyer Brokerage on Deal {deal['deal_number']} ({deal['quantity_tonnes']} MT @ ₹{deal['buyer_brokerage_rate_per_tonne']}/MT)"
                })
            if s_brok > 0:
                entries.append({
                    "account_name": seller["name"],
                    "busy_ledger_id": seller.get("busy_ledger_id") or f"BUSY_PARTY_{seller['id']}",
                    "debit": s_brok,
                    "credit": 0.0,
                    "narration": f"Seller Brokerage on Deal {deal['deal_number']} ({deal['quantity_tonnes']} MT @ ₹{deal['seller_brokerage_rate_per_tonne']}/MT)"
                })

            if total_brok > 0:
                entries.append({
                    "account_name": "BROKERAGE COMMISSION INCOME A/C",
                    "busy_ledger_id": "BUSY_INC_BROKERAGE",
                    "debit": 0.0,
                    "credit": total_brok,
                    "narration": f"Total Brokerage income on deal {deal['deal_number']}"
                })

            voucher_data = {
                "voucher_type": "Journal",
                "voucher_series": "JOURNAL",
                "voucher_date": datetime.now().strftime("%d-%m-%Y"),
                "deal_number": deal["deal_number"],
                "total_amount": total_brok,
                "entries": entries
            }

            return voucher_data
