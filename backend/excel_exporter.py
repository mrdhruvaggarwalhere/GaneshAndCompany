"""
G&C Central Deal and Brokerage Automation Platform
Multi-Tab Professional Excel (.xlsx) Generation Engine
Implements strict A:G column mapping and extended analytical columns.
"""
import io
import json
import os
import xlsxwriter
from datetime import datetime
from typing import Dict, Any, List, Optional
from database import get_db, rows_to_dict_list, row_to_dict
from models import format_iso_to_display, format_inr
from calculations import to_decimal


def create_excel_workbook(
    deals_data: List[Dict[str, Any]],
    chains_data: Optional[List[Dict[str, Any]]] = None,
    parties_data: Optional[List[Dict[str, Any]]] = None,
    products_data: Optional[List[Dict[str, Any]]] = None,
    audit_data: Optional[List[Dict[str, Any]]] = None,
    version: int = 1,
    exported_by: str = "Administrator"
) -> io.BytesIO:
    """
    Generates a full-featured multi-sheet Excel workbook as a BytesIO stream.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'remove_timezone': True})

    # Color Palette & Formats
    NAVY = "#0f172a"
    GOLD = "#f59e0b"
    LIGHT_GRAY = "#f8fafc"
    BORDER_COLOR = "#cbd5e1"

    fmt_title = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'font_color': '#ffffff',
        'bg_color': NAVY,
        'align': 'left',
        'valign': 'vcenter',
        'border': 1,
        'border_color': NAVY
    })

    fmt_subtitle = workbook.add_format({
        'font_size': 9,
        'font_color': '#64748b',
        'italic': True
    })

    fmt_header_mandatory = workbook.add_format({
        'bold': True,
        'font_size': 10,
        'font_color': '#ffffff',
        'bg_color': '#1e293b',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'border_color': '#334155',
        'text_wrap': True
    })

    fmt_header_extended = workbook.add_format({
        'bold': True,
        'font_size': 10,
        'font_color': '#0f172a',
        'bg_color': '#e2e8f0',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'border_color': '#cbd5e1',
        'text_wrap': True
    })

    fmt_cell = workbook.add_format({
        'font_size': 9.5,
        'border': 1,
        'border_color': BORDER_COLOR,
        'valign': 'vcenter'
    })

    fmt_cell_center = workbook.add_format({
        'font_size': 9.5,
        'align': 'center',
        'border': 1,
        'border_color': BORDER_COLOR,
        'valign': 'vcenter'
    })

    fmt_currency = workbook.add_format({
        'font_size': 9.5,
        'num_format': '₹ #,##,##0.00',
        'align': 'right',
        'border': 1,
        'border_color': BORDER_COLOR,
        'valign': 'vcenter'
    })

    fmt_rate = workbook.add_format({
        'font_size': 9.5,
        'num_format': '₹ #,##0.00',
        'align': 'right',
        'border': 1,
        'border_color': BORDER_COLOR,
        'valign': 'vcenter'
    })

    fmt_qty = workbook.add_format({
        'font_size': 9.5,
        'num_format': '#,##0.000',
        'align': 'right',
        'border': 1,
        'border_color': BORDER_COLOR,
        'valign': 'vcenter'
    })

    fmt_pct = workbook.add_format({
        'font_size': 9.5,
        'num_format': '0.0"%"',
        'align': 'center',
        'border': 1,
        'border_color': BORDER_COLOR,
        'valign': 'vcenter'
    })

    fmt_total = workbook.add_format({
        'bold': True,
        'font_size': 10,
        'bg_color': '#f1f5f9',
        'border': 1,
        'border_color': '#94a3b8',
        'num_format': '₹ #,##,##0.00',
        'valign': 'vcenter'
    })

    fmt_total_qty = workbook.add_format({
        'bold': True,
        'font_size': 10,
        'bg_color': '#f1f5f9',
        'border': 1,
        'border_color': '#94a3b8',
        'num_format': '#,##0.000',
        'align': 'right',
        'valign': 'vcenter'
    })

    # =========================================================================
    # SHEET 1: DEALS (Strict A:G mapping + Extended columns from H)
    # =========================================================================
    ws_deals = workbook.add_worksheet('Deals')
    ws_deals.set_landscape()
    ws_deals.set_margins(0.5, 0.5, 0.5, 0.5)

    # Title Block
    ws_deals.merge_range('A1:G1', 'GANESH & COMPANY - DEALS REGISTER (EXCEL A:G MAPPING)', fmt_title)
    ws_deals.write('A2', f"Exported on: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Version: v{version} | By: {exported_by}", fmt_subtitle)

    headers_mandatory = [
        ("Deal/Seller Date\n[Col A]", 15),
        ("Buyer\n[Col B]", 28),
        ("Seller\n[Col C]", 28),
        ("Product\n[Col D]", 12),
        ("Quantity\n[Col E]", 15),
        ("Price and GST\n[Col F]", 18),
        ("Delivery Date\n[Col G]", 15)
    ]

    headers_extended = [
        ("Deal ID\n[Col H]", 14),
        ("Chain ID\n[Col I]", 14),
        ("Qty (Tonnes)\n[Col J]", 14),
        ("Rate/Qtl (₹)\n[Col K]", 14),
        ("GST %\n[Col L]", 10),
        ("Authorized Rate (₹)\n[Col M]", 16),
        ("Actual Rate (₹)\n[Col N]", 16),
        ("Price Diff/Qtl (₹)\n[Col O]", 16),
        ("Price Diff Profit (₹)\n[Col P]", 18),
        ("Buyer Brok Rate\n[Col Q]", 15),
        ("Buyer Brok (₹)\n[Col R]", 15),
        ("Seller Brok Rate\n[Col S]", 15),
        ("Seller Brok (₹)\n[Col T]", 15),
        ("Total Brokerage (₹)\n[Col U]", 18),
        ("Total Earning (₹)\n[Col V]", 18),
        ("Status\n[Col W]", 12),
        ("Original Bill Seller\n[Col X]", 25),
        ("Final Bill Buyer\n[Col Y]", 25),
        ("Created By\n[Col Z]", 14),
        ("Created At\n[Col AA]", 18)
    ]

    # Write Headers (Row 3, 0-indexed is row 3 -> row_idx=3)
    row_idx = 3
    col_idx = 0
    for h_name, width in headers_mandatory:
        ws_deals.write(row_idx, col_idx, h_name, fmt_header_mandatory)
        ws_deals.set_column(col_idx, col_idx, width)
        col_idx += 1

    for h_name, width in headers_extended:
        ws_deals.write(row_idx, col_idx, h_name, fmt_header_extended)
        ws_deals.set_column(col_idx, col_idx, width)
        col_idx += 1

    ws_deals.set_row(row_idx, 30)

    # Freeze panes on data row
    ws_deals.freeze_panes(4, 3)

    # Populate Deals rows
    data_start_row = 4
    for idx, d in enumerate(deals_data):
        curr_row = data_start_row + idx

        # Column A: Deal/Seller Date
        deal_date_disp = format_iso_to_display(d.get("deal_date") or d.get("instruction_date"))
        ws_deals.write(curr_row, 0, deal_date_disp, fmt_cell_center)

        # Column B: Buyer
        ws_deals.write(curr_row, 1, d.get("buyer_name", ""), fmt_cell)

        # Column C: Seller
        seller_display = d.get("seller_name", "")
        if d.get("authorized_rate_per_qtl") and float(d.get("authorized_rate_per_qtl", 0)) > 0:
            seller_display += f" .@{float(d['authorized_rate_per_qtl']):g}/-"
        ws_deals.write(curr_row, 2, seller_display, fmt_cell)

        # Column D: Product
        ws_deals.write(curr_row, 3, d.get("product_code") or d.get("product_name", "M.OIL"), fmt_cell_center)

        # Column E: Quantity (quintals / tonnes)
        qty_qtl = float(d.get("quantity_qtl", 0))
        qty_tonnes = float(d.get("quantity_tonnes", qty_qtl / 10))
        qty_display = f"{qty_tonnes:g} MT ({qty_qtl:g} Qtl)"
        ws_deals.write(curr_row, 4, qty_display, fmt_cell_center)

        # Column F: Price and GST
        rate_val = float(d.get("rate_per_qtl", d.get("actual_rate_per_qtl", 0)))
        gst_txt = "+GST" if d.get("gst_applicable", 1) else "Incl."
        price_gst_disp = f"{rate_val:g}+{gst_txt}" if d.get("gst_applicable", 1) else f"{rate_val:g} {gst_txt}"
        ws_deals.write(curr_row, 5, price_gst_disp, fmt_cell_center)

        # Column G: Delivery Date
        del_date_disp = format_iso_to_display(d.get("delivery_date"))
        ws_deals.write(curr_row, 6, del_date_disp, fmt_cell_center)

        # Extended technical fields (H+)
        ws_deals.write(curr_row, 7, d.get("deal_number", f"DL-{d.get('id', '')}"), fmt_cell_center)
        ws_deals.write(curr_row, 8, d.get("chain_code", f"CHN-{d.get('chain_id', '')}"), fmt_cell_center)
        ws_deals.write(curr_row, 9, qty_tonnes, fmt_qty)
        ws_deals.write(curr_row, 10, rate_val, fmt_rate)
        ws_deals.write(curr_row, 11, float(d.get("gst_pct", 5.0)), fmt_pct)
        ws_deals.write(curr_row, 12, float(d.get("authorized_rate_per_qtl", 0)), fmt_rate)
        ws_deals.write(curr_row, 13, float(d.get("actual_rate_per_qtl", rate_val)), fmt_rate)
        ws_deals.write(curr_row, 14, float(d.get("price_diff_per_qtl", 0)), fmt_rate)
        ws_deals.write(curr_row, 15, float(d.get("price_diff_profit", 0)), fmt_currency)
        ws_deals.write(curr_row, 16, float(d.get("buyer_brokerage_rate_per_tonne", 0)), fmt_rate)
        ws_deals.write(curr_row, 17, float(d.get("buyer_brokerage_amount", 0)), fmt_currency)
        ws_deals.write(curr_row, 18, float(d.get("seller_brokerage_rate_per_tonne", 0)), fmt_rate)
        ws_deals.write(curr_row, 19, float(d.get("seller_brokerage_amount", 0)), fmt_currency)
        ws_deals.write(curr_row, 20, float(d.get("total_brokerage", 0)), fmt_currency)
        ws_deals.write(curr_row, 21, float(d.get("total_deal_earning", 0)), fmt_currency)
        ws_deals.write(curr_row, 22, (d.get("status") or "confirmed").upper(), fmt_cell_center)
        ws_deals.write(curr_row, 23, d.get("original_bill_seller_name", ""), fmt_cell)
        ws_deals.write(curr_row, 24, d.get("final_bill_buyer_name", ""), fmt_cell)
        ws_deals.write(curr_row, 25, d.get("creator_name", "Broker"), fmt_cell_center)
        ws_deals.write(curr_row, 26, str(d.get("created_at", "")), fmt_cell_center)

    # Summary Totals row
    if deals_data:
        total_row = data_start_row + len(deals_data)
        ws_deals.merge_range(total_row, 0, total_row, 8, "TOTALS", fmt_total)
        # Quantity formula
        ws_deals.write_formula(total_row, 9, f"=SUM(J5:J{total_row})", fmt_total_qty)
        ws_deals.write(total_row, 10, "", fmt_total)
        ws_deals.write(total_row, 11, "", fmt_total)
        ws_deals.write(total_row, 12, "", fmt_total)
        ws_deals.write(total_row, 13, "", fmt_total)
        ws_deals.write(total_row, 14, "", fmt_total)
        # Price diff profit total
        ws_deals.write_formula(total_row, 15, f"=SUM(P5:P{total_row})", fmt_total)
        ws_deals.write(total_row, 16, "", fmt_total)
        # Buyer brok total
        ws_deals.write_formula(total_row, 17, f"=SUM(R5:R{total_row})", fmt_total)
        ws_deals.write(total_row, 18, "", fmt_total)
        # Seller brok total
        ws_deals.write_formula(total_row, 19, f"=SUM(T5:T{total_row})", fmt_total)
        # Total brokerage
        ws_deals.write_formula(total_row, 20, f"=SUM(U5:U{total_row})", fmt_total)
        # Total earnings
        ws_deals.write_formula(total_row, 21, f"=SUM(V5:V{total_row})", fmt_total)

    # =========================================================================
    # SHEET 2: DEAL CHAINS & OFFICIAL DIRECT BILLING
    # =========================================================================
    if chains_data:
        ws_chains = workbook.add_worksheet('Deal Chains & Direct Billing')
        ws_chains.merge_range('A1:H1', 'GANESH & COMPANY - DEAL CHAINS & OFFICIAL DIRECT BILLING INSTRUCTIONS', fmt_title)
        chain_headers = [
            ("Chain Code", 16),
            ("Product", 12),
            ("Lot Qty (Qtl)", 14),
            ("Lot Qty (Tonnes)", 15),
            ("Original Bill Seller", 28),
            ("Final Bill Buyer", 28),
            ("Final Rate (₹)", 15),
            ("Official Billing Instruction", 45),
            ("Price Diff Profit (₹)", 18),
            ("Total Brokerage (₹)", 18),
            ("Total Earning (₹)", 18),
            ("Chain Status", 14)
        ]
        r = 3
        for c_idx, (h_text, w) in enumerate(chain_headers):
            ws_chains.write(r, c_idx, h_text, fmt_header_mandatory)
            ws_chains.set_column(c_idx, c_idx, w)

        for c_row_idx, ch in enumerate(chains_data):
            curr = r + 1 + c_row_idx
            ws_chains.write(curr, 0, ch.get("chain_code", ""), fmt_cell_center)
            ws_chains.write(curr, 1, ch.get("product_name", ""), fmt_cell_center)
            ws_chains.write(curr, 2, float(ch.get("initial_quantity_qtl", 0)), fmt_qty)
            ws_chains.write(curr, 3, float(ch.get("initial_quantity_qtl", 0)) / 10.0, fmt_qty)
            ws_chains.write(curr, 4, ch.get("original_bill_seller_name", ""), fmt_cell)
            ws_chains.write(curr, 5, ch.get("final_bill_buyer_name", ""), fmt_cell)
            ws_chains.write(curr, 6, float(ch.get("final_billing_rate", 0)), fmt_rate)
            ws_chains.write(curr, 7, ch.get("direct_billing_instruction", ""), fmt_cell)
            ws_chains.write(curr, 8, float(ch.get("total_price_diff_profit", 0)), fmt_currency)
            ws_chains.write(curr, 9, float(ch.get("total_brokerage", 0)), fmt_currency)
            ws_chains.write(curr, 10, float(ch.get("total_chain_earning", 0)), fmt_currency)
            ws_chains.write(curr, 11, ch.get("status", "").upper(), fmt_cell_center)

    # =========================================================================
    # SHEET 3: PARTIES & BROKERAGE RECEIVABLES
    # =========================================================================
    if parties_data:
        ws_parties = workbook.add_worksheet('Party Ledger & Receivables')
        ws_parties.merge_range('A1:G1', 'GANESH & COMPANY - PARTY MASTER & BROKERAGE RECEIVABLES', fmt_title)
        party_headers = [
            ("Party Name", 30),
            ("Type", 12),
            ("City / State", 20),
            ("GSTIN", 18),
            ("Default Buyer Brok", 18),
            ("Default Seller Brok", 18),
            ("Brokerage Charged (₹)", 20),
            ("Brokerage Received (₹)", 20),
            ("Outstanding Balance (₹)", 22),
            ("BUSY Ledger ID", 16)
        ]
        r = 3
        for c_idx, (h_text, w) in enumerate(party_headers):
            ws_parties.write(r, c_idx, h_text, fmt_header_mandatory)
            ws_parties.set_column(c_idx, c_idx, w)

        for p_idx, p in enumerate(parties_data):
            curr = r + 1 + p_idx
            ws_parties.write(curr, 0, p.get("name", ""), fmt_cell)
            ws_parties.write(curr, 1, (p.get("party_type") or "").upper(), fmt_cell_center)
            ws_parties.write(curr, 2, f"{p.get('city', '')}, {p.get('state', '')}".strip(", "), fmt_cell)
            ws_parties.write(curr, 3, p.get("gstin", "") or "N/A", fmt_cell_center)
            ws_parties.write(curr, 4, float(p.get("default_buyer_brokerage_rate", 0)), fmt_rate)
            ws_parties.write(curr, 5, float(p.get("default_seller_brokerage_rate", 0)), fmt_rate)
            ws_parties.write(curr, 6, float(p.get("total_brokerage_charged", 0)), fmt_currency)
            ws_parties.write(curr, 7, float(p.get("total_brokerage_paid", 0)), fmt_currency)
            ws_parties.write(curr, 8, float(p.get("outstanding_brokerage", 0)), fmt_currency)
            ws_parties.write(curr, 9, p.get("busy_ledger_id", "") or "UNMAPPED", fmt_cell_center)

    # =========================================================================
    # SHEET 4: AUDIT TRAIL LOG
    # =========================================================================
    if audit_data:
        ws_audit = workbook.add_worksheet('Audit Trail')
        ws_audit.merge_range('A1:F1', 'GANESH & COMPANY - IMMUTABLE AUDIT TRAIL LOG', fmt_title)
        audit_headers = [
            ("Timestamp", 20),
            ("User", 15),
            ("Action", 14),
            ("Entity Type", 14),
            ("Entity ID", 14),
            ("Notes / Summary", 40)
        ]
        r = 3
        for c_idx, (h_text, w) in enumerate(audit_headers):
            ws_audit.write(r, c_idx, h_text, fmt_header_mandatory)
            ws_audit.set_column(c_idx, c_idx, w)

        for a_idx, a in enumerate(audit_data):
            curr = r + 1 + a_idx
            ws_audit.write(curr, 0, str(a.get("timestamp", "")), fmt_cell_center)
            ws_audit.write(curr, 1, a.get("username", "system"), fmt_cell_center)
            ws_audit.write(curr, 2, a.get("action", ""), fmt_cell_center)
            ws_audit.write(curr, 3, a.get("entity_type", ""), fmt_cell_center)
            ws_audit.write(curr, 4, str(a.get("entity_id", "")), fmt_cell_center)
            ws_audit.write(curr, 5, a.get("notes", "") or "", fmt_cell)

    workbook.close()
    output.seek(0)
    return output
