"""
G&C Central Deal and Brokerage Automation Platform
REST API & Web Application Server
"""
import os
import json
import urllib.parse
import traceback
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional

from database import get_db, init_db, row_to_dict, rows_to_dict_list, DB_PATH
from calculations import (
    to_decimal,
    convert_quintals_to_tonnes,
    convert_tonnes_to_quintals,
    calculate_price_difference_profit,
    calculate_deal_brokerage,
    compute_deal_summary,
    compute_chain_totals,
    round_currency
)
from models import (
    validate_deal_data,
    validate_party_data,
    validate_product_data,
    normalize_name,
    parse_date_to_iso,
    format_iso_to_display,
    format_inr
)
from auth_audit import (
    authenticate_user,
    get_current_user,
    check_permission,
    log_audit,
    get_audit_trail
)
from excel_exporter import create_excel_workbook
from busy_adapter import BusyAccountingAdapter
from seed_data import seed_database
from tests import run_all_tests
from communication_service import (
    normalize_indian_phone,
    validate_email,
    generate_communication_draft,
    COMM_MODES
)

PORT = int(os.environ.get("PORT", 8000))
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


class GncApiHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data: Any, status_code: int = 200):
        """Helper to send JSON responses with proper headers and decimal serialization."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return str(obj)

        payload = json.dumps(data, default=decimal_default)
        self.wfile.write(payload.encode("utf-8"))

    def _send_error(self, message: str, status_code: int = 400):
        self._send_json({"success": False, "error": message}, status_code=status_code)

    def _send_binary(self, binary_data: bytes, filename: str, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(binary_data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(binary_data)

    def _get_auth_user(self) -> Optional[Dict[str, Any]]:
        auth_header = self.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip() if auth_header else None
        return get_current_user(token)

    def _read_body_json(self) -> Dict[str, Any]:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        raw_body = self.rfile.read(content_length).decode('utf-8')
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        """Route API GET endpoints or serve static frontend assets."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            try:
                self._handle_api_get(path, query)
            except Exception as e:
                traceback.print_exc()
                self._send_error(f"Internal Server Error: {str(e)}", status_code=500)
        else:
            # Serve frontend files or fallback to index.html
            if path == "/" or not os.path.exists(os.path.join(STATIC_DIR, path.lstrip("/"))):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        """Route API POST endpoints."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            try:
                self._handle_api_post(path)
            except Exception as e:
                traceback.print_exc()
                self._send_error(f"Error processing request: {str(e)}", status_code=500)
        else:
            self._send_error("Not found", 404)

    def do_PUT(self):
        """Route API PUT endpoints."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            try:
                self._handle_api_put(path)
            except Exception as e:
                traceback.print_exc()
                self._send_error(f"Error processing request: {str(e)}", status_code=500)
        else:
            self._send_error("Not found", 404)

    def do_PATCH(self):
        """Route API PATCH endpoints."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            try:
                self._handle_api_patch(path)
            except Exception as e:
                traceback.print_exc()
                self._send_error(f"Error processing request: {str(e)}", status_code=500)
        else:
            self._send_error("Not found", 404)

    # =========================================================================
    # API GET ROUTER
    # =========================================================================
    def _handle_api_get(self, path: str, query: Dict[str, List[str]]):
        user = self._get_auth_user()

        # 1. Health check
        if path == "/api/health":
            self._send_json({"status": "healthy", "service": "G&C Central Automation Platform", "time": datetime.now().isoformat()})
            return

        # 2. Current User
        if path == "/api/auth/me":
            self._send_json({"success": True, "user": user})
            return

        # 3. Acceptance test runner
        if path == "/api/tests/run":
            results = run_all_tests()
            self._send_json({"success": True, "results": results})
            return

        # 4. Dashboard KPIs
        if path == "/api/dashboard":
            self._get_dashboard_data()
            return

        # 5. Parties
        if path == "/api/parties":
            self._get_parties()
            return

        # 5b. Single party ledger
        if path.startswith("/api/parties/") and path.endswith("/ledger"):
            party_id = int(path.split("/")[3])
            self._get_party_ledger(party_id, query)
            return

        # 6. Products
        if path == "/api/products":
            self._get_products()
            return

        # 7. Deals List
        if path == "/api/deals":
            self._get_deals(query)
            return

        # 7b. Single Deal
        if path.startswith("/api/deals/") and not path.endswith("/cancel"):
            deal_id = int(path.split("/")[3])
            self._get_deal_detail(deal_id)
            return

        # 8. Deal Chains List
        if path == "/api/chains":
            self._get_chains(query)
            return

        # 8b. Single Deal Chain with Visual Timeline & Links
        if path.startswith("/api/chains/") and not path.endswith("/approve-billing") and not path.endswith("/resell"):
            chain_id = int(path.split("/")[3])
            self._get_chain_detail(chain_id)
            return

        # 9. Reports
        if path == "/api/reports":
            report_type = query.get("type", ["deals"])[0]
            self._get_report_data(report_type, query)
            return

        # 10. Excel Export
        if path == "/api/export/excel":
            self._export_excel(query, user)
            return

        # 11. BUSY Mappings & Sync Queue
        if path == "/api/busy/mappings":
            self._get_busy_mappings()
            return

        if path == "/api/busy/queue":
            self._get_busy_queue()
            return

        # 12. Audit Trail
        if path == "/api/audit":
            entity_type = query.get("entity_type", [None])[0]
            entity_id = query.get("entity_id", [None])[0]
            trail = get_audit_trail(entity_type, entity_id)
            self._send_json({"success": True, "audit_events": trail})
            return

        # 13. Deleted Items / Trash / Recycle Bin
        if path in ("/api/trash", "/api/deleted"):
            self._get_deleted_items(query)
            return

        # 14. Communications History Log
        if path == "/api/communications":
            self._get_communications(query)
            return

        self._send_error("API route not found", 404)

    # =========================================================================
    # API POST ROUTER
    # =========================================================================
    def _handle_api_post(self, path: str):
        body = self._read_body_json()
        user = self._get_auth_user()
        user_id = user["user_id"] if user else 1
        username = user["username"] if user else "system"

        # 1. Login
        if path == "/api/auth/login":
            username_in = body.get("username", "")
            password_in = body.get("password", "")
            session = authenticate_user(username_in, password_in)
            if session:
                self._send_json({"success": True, "session": session})
            else:
                self._send_error("Invalid username or password", 401)
            return

        # 2. Create Initial Deal & Chain
        if path == "/api/deals":
            self._create_initial_deal(body, user_id, username)
            return

        # 3. Resell / Add Next Link in Chain
        if path.startswith("/api/chains/") and path.endswith("/resell"):
            chain_id = int(path.split("/")[3])
            self._add_chain_resale(chain_id, body, user_id, username)
            return

        # 4. Cancel Deal
        if path.startswith("/api/deals/") and path.endswith("/cancel"):
            deal_id = int(path.split("/")[3])
            self._cancel_deal(deal_id, body, user_id, username)
            return

        # 4b. Delete Deal (Soft delete with undo)
        if path.startswith("/api/deals/") and path.endswith("/delete"):
            deal_id = int(path.split("/")[3])
            self._delete_deal(deal_id, body, user_id, username)
            return

        # 4c. Restore Deal (Undo delete)
        if path.startswith("/api/deals/") and path.endswith("/restore"):
            deal_id = int(path.split("/")[3])
            self._restore_deal(deal_id, user_id, username)
            return

        # 4d. Delete Chain (Soft delete with undo)
        if path.startswith("/api/chains/") and path.endswith("/delete"):
            chain_id = int(path.split("/")[3])
            self._delete_chain(chain_id, body, user_id, username)
            return

        # 4e. Restore Chain (Undo delete)
        if path.startswith("/api/chains/") and path.endswith("/restore"):
            chain_id = int(path.split("/")[3])
            self._restore_chain(chain_id, user_id, username)
            return

        # 5. Approve Official Billing Instruction
        if path.startswith("/api/chains/") and path.endswith("/approve-billing"):
            chain_id = int(path.split("/")[3])
            self._approve_chain_billing(chain_id, body, user_id, username)
            return

        # 6. Party CRUD
        if path == "/api/parties":
            self._create_party(body, user_id, username)
            return

        # 6b. Delete Party
        if path.startswith("/api/parties/") and path.endswith("/delete"):
            party_id = int(path.split("/")[3])
            self._delete_party(party_id, body, user_id, username)
            return

        # 6c. Restore Party
        if path.startswith("/api/parties/") and path.endswith("/restore"):
            party_id = int(path.split("/")[3])
            self._restore_party(party_id, user_id, username)
            return

        # 7. Record Brokerage Payment
        if path.startswith("/api/parties/") and path.endswith("/payments"):
            party_id = int(path.split("/")[3])
            self._record_party_payment(party_id, body, user_id, username)
            return

        # 7b. Delete Payment
        if path.startswith("/api/payments/") and path.endswith("/delete"):
            payment_id = int(path.split("/")[3])
            self._delete_payment(payment_id, body, user_id, username)
            return

        # 7c. Restore Payment
        if path.startswith("/api/payments/") and path.endswith("/restore"):
            payment_id = int(path.split("/")[3])
            self._restore_payment(payment_id, user_id, username)
            return

        # 8. Product CRUD
        if path == "/api/products":
            self._create_product(body, user_id, username)
            return

        # 8b. Delete Product
        if path.startswith("/api/products/") and path.endswith("/delete"):
            product_id = int(path.split("/")[3])
            self._delete_product(product_id, body, user_id, username)
            return

        # 8c. Restore Product
        if path.startswith("/api/products/") and path.endswith("/restore"):
            product_id = int(path.split("/")[3])
            self._restore_product(product_id, user_id, username)
            return

        # 9. BUSY Generate Voucher / Stage
        if path == "/api/busy/generate-voucher":
            self._stage_busy_voucher(body, user_id, username)
            return

        # 10. BUSY Sync Trigger
        if path == "/api/busy/sync":
            self._sync_busy_voucher(body, user_id, username)
            return

        # 11. Undo Action from Audit Log
        if path.startswith("/api/audit/") and path.endswith("/undo"):
            event_id = int(path.split("/")[3])
            self._undo_audit_event(event_id, user_id, username)
            return

        # 12. Communications: Prepare Draft
        if path == "/api/communications/prepare":
            self._prepare_communication(body)
            return

        # 13. Communications: Log Triggered Draft (WhatsApp opened / Email draft opened)
        if path == "/api/communications/log":
            self._log_communication(body, user_id, username)
            return

        # 14. Communications: Update Status
        if path.startswith("/api/communications/") and path.endswith("/status"):
            comm_id = int(path.split("/")[3])
            self._update_communication_status(comm_id, body, user_id, username)
            return

        self._send_error("API POST route not found", 404)

    # =========================================================================
    # API PUT ROUTER
    # =========================================================================
    def _handle_api_put(self, path: str):
        body = self._read_body_json()
        user = self._get_auth_user()
        user_id = user["user_id"] if user else 1
        username = user["username"] if user else "system"

        if path.startswith("/api/deals/"):
            deal_id = int(path.split("/")[3])
            self._update_deal(deal_id, body, user_id, username)
            return

        if path.startswith("/api/parties/"):
            party_id = int(path.split("/")[3])
            self._update_party(party_id, body, user_id, username)
            return

        if path.startswith("/api/products/"):
            product_id = int(path.split("/")[3])
            self._update_product(product_id, body, user_id, username)
            return

        if path.startswith("/api/communications/") and path.endswith("/status"):
            comm_id = int(path.split("/")[3])
            self._update_communication_status(comm_id, body, user_id, username)
            return

        self._send_error("API PUT route not found", 404)

    # =========================================================================
    # API PATCH ROUTER
    # =========================================================================
    def _handle_api_patch(self, path: str):
        body = self._read_body_json()
        user = self._get_auth_user()
        user_id = user["user_id"] if user else 1
        username = user["username"] if user else "system"

        if path.startswith("/api/communications/") and path.endswith("/status"):
            comm_id = int(path.split("/")[3])
            self._update_communication_status(comm_id, body, user_id, username)
            return

        self._send_error("API PATCH route not found", 404)

    # =========================================================================
    # BUSINESS LOGIC & HANDLERS
    # =========================================================================

    def _get_dashboard_data(self):
        with get_db() as conn:
            # Active and total counts
            total_deals = conn.execute("SELECT COUNT(*) FROM deals WHERE status != 'cancelled' AND COALESCE(is_deleted, 0) = 0").fetchone()[0]
            total_chains = conn.execute("SELECT COUNT(*) FROM deal_chains WHERE status != 'cancelled' AND COALESCE(is_deleted, 0) = 0").fetchone()[0]
            chains_ready_billing = conn.execute("SELECT COUNT(*) FROM deal_chains WHERE status = 'ready_for_billing' AND COALESCE(is_deleted, 0) = 0").fetchone()[0]
            chains_in_progress = conn.execute("SELECT COUNT(*) FROM deal_chains WHERE status = 'in_progress' AND COALESCE(is_deleted, 0) = 0").fetchone()[0]

            # Financial Totals
            fin = conn.execute("""
                SELECT
                    COALESCE(SUM(price_diff_profit), 0) as total_profit,
                    COALESCE(SUM(buyer_brokerage_amount), 0) as total_buyer_brok,
                    COALESCE(SUM(seller_brokerage_amount), 0) as total_seller_brok,
                    COALESCE(SUM(total_brokerage), 0) as total_brok,
                    COALESCE(SUM(total_deal_earning), 0) as total_earning
                FROM deals WHERE status != 'cancelled' AND COALESCE(is_deleted, 0) = 0
            """).fetchone()

            # Brokerage payments received
            total_paid = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM brokerage_payments WHERE COALESCE(is_deleted, 0) = 0").fetchone()[0]
            outstanding_brok = fin["total_brok"] - total_paid

            # Deliveries Alerts
            today_iso = datetime.now().strftime("%Y-%m-%d")
            due_today = conn.execute("SELECT COUNT(*) FROM deals WHERE delivery_date = ? AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0", (today_iso,)).fetchone()[0]
            overdue = conn.execute("SELECT COUNT(*) FROM deals WHERE delivery_date < ? AND status = 'confirmed' AND COALESCE(is_deleted, 0) = 0", (today_iso,)).fetchone()[0]

            # Recent active transactions (excludes chains already approved for final commercial billing)
            recent_deals_rows = conn.execute("""
                SELECT d.*, b.name as buyer_name, s.name as seller_name, p.name as product_name, p.code as product_code,
                       c.chain_code, c.status as chain_status
                FROM deals d
                JOIN parties b ON d.buyer_id = b.id
                JOIN parties s ON d.seller_id = s.id
                JOIN products p ON d.product_id = p.id
                JOIN deal_chains c ON d.chain_id = c.id
                WHERE COALESCE(d.is_deleted, 0) = 0
                  AND c.status != 'billed'
                ORDER BY d.id DESC LIMIT 15
            """).fetchall()

            # Party-wise brokerage receivables top 5
            party_receivables = conn.execute("""
                SELECT p.id, p.name, p.city,
                       COALESCE(SUM(d.buyer_brokerage_amount), 0) + COALESCE(SUM(d2.seller_brokerage_amount), 0) as total_charged,
                       COALESCE((SELECT SUM(amount) FROM brokerage_payments WHERE party_id = p.id AND COALESCE(is_deleted, 0) = 0), 0) as total_paid
                FROM parties p
                LEFT JOIN deals d ON d.buyer_id = p.id AND d.status != 'cancelled' AND COALESCE(d.is_deleted, 0) = 0
                LEFT JOIN deals d2 ON d2.seller_id = p.id AND d2.status != 'cancelled' AND COALESCE(d2.is_deleted, 0) = 0
                WHERE COALESCE(p.is_deleted, 0) = 0
                GROUP BY p.id
                HAVING (total_charged - total_paid) > 0
                ORDER BY (total_charged - total_paid) DESC LIMIT 5
            """).fetchall()

            self._send_json({
                "success": True,
                "summary": {
                    "total_deals": total_deals,
                    "total_chains": total_chains,
                    "chains_ready_billing": chains_ready_billing,
                    "chains_in_progress": chains_in_progress,
                    "total_price_diff_profit": fin["total_profit"],
                    "total_buyer_brokerage": fin["total_buyer_brok"],
                    "total_seller_brokerage": fin["total_seller_brok"],
                    "total_brokerage": fin["total_brok"],
                    "total_earning": fin["total_earning"],
                    "total_brokerage_received": total_paid,
                    "outstanding_brokerage": outstanding_brok,
                    "due_today": due_today,
                    "overdue_deliveries": overdue
                },
                "recent_deals": rows_to_dict_list(recent_deals_rows),
                "party_receivables": rows_to_dict_list(party_receivables)
            })

    def _get_parties(self):
        with get_db() as conn:
            rows = conn.execute("""
                SELECT p.*,
                       COALESCE((SELECT SUM(buyer_brokerage_amount) FROM deals WHERE buyer_id = p.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0), 0) +
                       COALESCE((SELECT SUM(seller_brokerage_amount) FROM deals WHERE seller_id = p.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0), 0) as total_brokerage_charged,
                       COALESCE((SELECT SUM(amount) FROM brokerage_payments WHERE party_id = p.id AND COALESCE(is_deleted, 0) = 0), 0) as total_brokerage_paid,
                       COALESCE((SELECT SUM(price_diff_profit) FROM deals WHERE (buyer_id = p.id OR seller_id = p.id) AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0), 0) as total_chain_profit,
                       (SELECT COUNT(*) FROM deals WHERE (buyer_id = p.id OR seller_id = p.id) AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as total_deals_count
                FROM parties p
                WHERE COALESCE(p.is_deleted, 0) = 0
                ORDER BY p.name ASC
            """).fetchall()

            result = []
            for r in rows:
                d = dict(r)
                d["outstanding_brokerage"] = d["total_brokerage_charged"] - d["total_brokerage_paid"]
                result.append(d)

            self._send_json({"success": True, "parties": result})

    def _get_party_ledger(self, party_id: int, query: Dict[str, List[str]]):
        with get_db() as conn:
            party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (party_id,)).fetchone())
            if not party:
                self._send_error("Party not found", 404)
                return

            deals = conn.execute("""
                SELECT d.*, b.name as buyer_name, s.name as seller_name, p.name as product_name, p.code as product_code,
                       c.chain_code,
                       CASE WHEN d.buyer_id = ? THEN 'BUYER' ELSE 'SELLER' END as party_role,
                       CASE WHEN d.buyer_id = ? THEN d.buyer_brokerage_amount ELSE d.seller_brokerage_amount END as party_brokerage
                FROM deals d
                JOIN parties b ON d.buyer_id = b.id
                JOIN parties s ON d.seller_id = s.id
                JOIN products p ON d.product_id = p.id
                JOIN deal_chains c ON d.chain_id = c.id
                WHERE (d.buyer_id = ? OR d.seller_id = ?) AND d.status != 'cancelled' AND COALESCE(d.is_deleted, 0) = 0
                ORDER BY d.deal_date ASC, d.id ASC
            """, (party_id, party_id, party_id, party_id)).fetchall()

            payments = conn.execute("""
                SELECT * FROM brokerage_payments WHERE party_id = ? AND COALESCE(is_deleted, 0) = 0 ORDER BY payment_date ASC, id ASC
            """, (party_id,)).fetchall()

            total_charged = sum(d["party_brokerage"] for d in deals)
            total_paid = sum(p["amount"] for p in payments)
            total_profit_generated = sum(d["price_diff_profit"] for d in deals if d["price_diff_profit"] > 0)

            self._send_json({
                "success": True,
                "party": party,
                "deals": rows_to_dict_list(deals),
                "payments": rows_to_dict_list(payments),
                "summary": {
                    "total_deals": len(deals),
                    "total_brokerage_charged": total_charged,
                    "total_chain_profit": total_profit_generated,
                    "total_brokerage_paid": total_paid,
                    "outstanding_balance": total_charged - total_paid,
                    "total_overall_earnings": total_charged + total_profit_generated
                }
            })

    def _create_party(self, body: Dict[str, Any], user_id: int, username: str):
        is_valid, err = validate_party_data(body)
        if not is_valid:
            self._send_error(err)
            return

        with get_db() as conn:
            norm_name = normalize_name(body["name"])
            existing = conn.execute("SELECT id FROM parties WHERE normalized_name = ? AND COALESCE(is_deleted, 0) = 0", (norm_name,)).fetchone()
            if existing:
                self._send_error("A party with a matching normalized name already exists.")
                return

            wa_prim = normalize_indian_phone(body.get("whatsapp_primary") or body.get("phone"))
            wa_sec = normalize_indian_phone(body.get("whatsapp_secondary"))
            em_prim = (body.get("email_primary") or body.get("email") or "").strip()
            em_sec = (body.get("email_secondary") or "").strip()

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO parties (
                    name, normalized_name, party_type, contact_person, phone, email,
                    address, city, state, gstin, default_buyer_brokerage_rate,
                    default_seller_brokerage_rate, brokerage_enabled, credit_notes, busy_ledger_id,
                    whatsapp_primary, whatsapp_secondary, email_primary, email_secondary,
                    preferred_comm_method, preferred_language, whatsapp_enabled, email_enabled,
                    comm_consent_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                body["name"].strip(),
                norm_name,
                body.get("party_type", "both"),
                body.get("contact_person"),
                body.get("phone") or wa_prim,
                body.get("email") or em_prim,
                body.get("address"),
                body.get("city"),
                body.get("state"),
                body.get("gstin"),
                float(body.get("default_buyer_brokerage_rate", 50.0)),
                float(body.get("default_seller_brokerage_rate", 50.0)),
                1 if body.get("brokerage_enabled", True) else 0,
                body.get("credit_notes"),
                body.get("busy_ledger_id"),
                wa_prim,
                wa_sec,
                em_prim,
                em_sec,
                body.get("preferred_comm_method", "both"),
                body.get("preferred_language", "english"),
                1 if body.get("whatsapp_enabled", True) else 0,
                1 if body.get("email_enabled", True) else 0,
                body.get("comm_consent_notes")
            ))
            party_id = cursor.lastrowid

            log_audit(
                user_id=user_id, username=username, action="CREATE",
                entity_type="party", entity_id=str(party_id),
                after_state=body, notes=f"Created party {body['name']}",
                conn=conn
            )

            self._send_json({"success": True, "party_id": party_id, "message": "Party created successfully."})

    def _update_party(self, party_id: int, body: Dict[str, Any], user_id: int, username: str):
        with get_db() as conn:
            old = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (party_id,)).fetchone())
            if not old:
                self._send_error("Party not found", 404)
                return

            wa_prim = normalize_indian_phone(body.get("whatsapp_primary", old.get("whatsapp_primary") or old.get("phone")))
            wa_sec = normalize_indian_phone(body.get("whatsapp_secondary", old.get("whatsapp_secondary")))
            em_prim = (body.get("email_primary", old.get("email_primary") or old.get("email")) or "").strip()
            em_sec = (body.get("email_secondary", old.get("email_secondary")) or "").strip()

            conn.execute("""
                UPDATE parties SET
                    name = ?, party_type = ?, contact_person = ?, phone = ?, email = ?,
                    address = ?, city = ?, state = ?, gstin = ?, default_buyer_brokerage_rate = ?,
                    default_seller_brokerage_rate = ?, brokerage_enabled = ?, credit_notes = ?,
                    busy_ledger_id = ?,
                    whatsapp_primary = ?, whatsapp_secondary = ?, email_primary = ?, email_secondary = ?,
                    preferred_comm_method = ?, preferred_language = ?, whatsapp_enabled = ?, email_enabled = ?,
                    comm_consent_notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                body.get("name", old["name"]),
                body.get("party_type", old["party_type"]),
                body.get("contact_person", old["contact_person"]),
                body.get("phone", old["phone"]) or wa_prim,
                body.get("email", old["email"]) or em_prim,
                body.get("address", old["address"]),
                body.get("city", old["city"]),
                body.get("state", old["state"]),
                body.get("gstin", old["gstin"]),
                float(body.get("default_buyer_brokerage_rate", old["default_buyer_brokerage_rate"])),
                float(body.get("default_seller_brokerage_rate", old["default_seller_brokerage_rate"])),
                1 if body.get("brokerage_enabled", True) else 0,
                body.get("credit_notes", old["credit_notes"]),
                body.get("busy_ledger_id", old["busy_ledger_id"]),
                wa_prim,
                wa_sec,
                em_prim,
                em_sec,
                body.get("preferred_comm_method", old.get("preferred_comm_method", "both")),
                body.get("preferred_language", old.get("preferred_language", "english")),
                1 if body.get("whatsapp_enabled", old.get("whatsapp_enabled", 1)) else 0,
                1 if body.get("email_enabled", old.get("email_enabled", 1)) else 0,
                body.get("comm_consent_notes", old.get("comm_consent_notes")),
                party_id
            ))

            log_audit(
                user_id=user_id, username=username, action="EDIT",
                entity_type="party", entity_id=str(party_id),
                before_state=old, after_state=body, notes=f"Updated party {body.get('name')}",
                conn=conn
            )

            self._send_json({"success": True, "message": "Party updated successfully."})

    def _delete_party(self, party_id: int, body: Dict[str, Any], user_id: int, username: str):
        reason = (body.get("reason") or "User deleted party").strip()
        with get_db() as conn:
            party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (party_id,)).fetchone())
            if not party:
                self._send_error("Party not found", 404)
                return
            conn.execute("""
                UPDATE parties SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by_user_id = ?, deletion_reason = ?
                WHERE id = ?
            """, (user_id, reason, party_id))
            log_audit(
                user_id=user_id, username=username, action="DELETE",
                entity_type="party", entity_id=str(party_id),
                before_state=party, notes=f"Deleted party {party['name']}: {reason}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Party '{party['name']}' deleted. You can restore it anytime from Deleted Items.", "party_id": party_id})

    def _restore_party(self, party_id: int, user_id: int, username: str):
        with get_db() as conn:
            party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (party_id,)).fetchone())
            if not party:
                self._send_error("Party not found", 404)
                return
            conn.execute("""
                UPDATE parties SET is_deleted = 0, deleted_at = NULL, deleted_by_user_id = NULL, deletion_reason = NULL
                WHERE id = ?
            """, (party_id,))
            log_audit(
                user_id=user_id, username=username, action="RESTORE",
                entity_type="party", entity_id=str(party_id),
                after_state={"is_deleted": 0}, notes=f"Restored party {party['name']}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Party '{party['name']}' restored successfully.", "party_id": party_id})

    def _record_party_payment(self, party_id: int, body: Dict[str, Any], user_id: int, username: str):
        amount = float(body.get("amount", 0))
        if amount <= 0:
            self._send_error("Payment amount must be positive.")
            return

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO brokerage_payments (
                    party_id, deal_id, payment_date, amount, payment_type, reference_number, bank_or_mode, notes, created_by_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                party_id,
                body.get("deal_id"),
                parse_date_to_iso(body.get("payment_date")) or datetime.now().strftime("%Y-%m-%d"),
                amount,
                body.get("payment_type", "receipt"),
                body.get("reference_number"),
                body.get("bank_or_mode", "Bank Transfer"),
                body.get("notes"),
                user_id
            ))
            payment_id = cursor.lastrowid

            log_audit(
                user_id=user_id, username=username, action="PAYMENT",
                entity_type="payment", entity_id=str(payment_id),
                after_state=body, notes=f"Recorded brokerage receipt ₹{amount} for party {party_id}",
                conn=conn
            )

            self._send_json({"success": True, "payment_id": payment_id, "message": "Payment recorded successfully."})

    def _delete_payment(self, payment_id: int, body: Dict[str, Any], user_id: int, username: str):
        reason = (body.get("reason") or "User deleted payment").strip()
        with get_db() as conn:
            payment = row_to_dict(conn.execute("SELECT * FROM brokerage_payments WHERE id = ?", (payment_id,)).fetchone())
            if not payment:
                self._send_error("Payment not found", 404)
                return
            conn.execute("""
                UPDATE brokerage_payments SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by_user_id = ?, deletion_reason = ?
                WHERE id = ?
            """, (user_id, reason, payment_id))
            log_audit(
                user_id=user_id, username=username, action="DELETE",
                entity_type="payment", entity_id=str(payment_id),
                before_state=payment, notes=f"Deleted payment receipt #{payment_id}: {reason}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Payment receipt #{payment_id} deleted. You can restore it anytime from Deleted Items.", "payment_id": payment_id})

    def _restore_payment(self, payment_id: int, user_id: int, username: str):
        with get_db() as conn:
            payment = row_to_dict(conn.execute("SELECT * FROM brokerage_payments WHERE id = ?", (payment_id,)).fetchone())
            if not payment:
                self._send_error("Payment not found", 404)
                return
            conn.execute("""
                UPDATE brokerage_payments SET is_deleted = 0, deleted_at = NULL, deleted_by_user_id = NULL, deletion_reason = NULL
                WHERE id = ?
            """, (payment_id,))
            log_audit(
                user_id=user_id, username=username, action="RESTORE",
                entity_type="payment", entity_id=str(payment_id),
                after_state={"is_deleted": 0}, notes=f"Restored payment #{payment_id}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Payment receipt #{payment_id} restored successfully.", "payment_id": payment_id})

    def _get_products(self):
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM products WHERE COALESCE(is_deleted, 0) = 0 ORDER BY name ASC").fetchall()
            self._send_json({"success": True, "products": rows_to_dict_list(rows)})

    def _create_product(self, body: Dict[str, Any], user_id: int, username: str):
        is_valid, err = validate_product_data(body)
        if not is_valid:
            self._send_error(err)
            return

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, code, default_unit, default_gst_pct, hsn_sac, busy_item_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                body["name"].strip(),
                body["code"].strip().upper(),
                body.get("default_unit", "quintals"),
                float(body.get("default_gst_pct", 5.0)),
                body.get("hsn_sac", "1514"),
                body.get("busy_item_id")
            ))
            product_id = cursor.lastrowid

            log_audit(
                user_id=user_id, username=username, action="CREATE",
                entity_type="product", entity_id=str(product_id),
                after_state=body, notes=f"Created product {body['name']}",
                conn=conn
            )

            self._send_json({"success": True, "product_id": product_id, "message": "Product created."})

    def _update_product(self, product_id: int, body: Dict[str, Any], user_id: int, username: str):
        with get_db() as conn:
            old = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())
            if not old:
                self._send_error("Product not found", 404)
                return

            conn.execute("""
                UPDATE products SET
                    name = ?, code = ?, default_unit = ?, default_gst_pct = ?, hsn_sac = ?,
                    busy_item_id = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                body.get("name", old["name"]),
                body.get("code", old["code"]),
                body.get("default_unit", old["default_unit"]),
                float(body.get("default_gst_pct", old["default_gst_pct"])),
                body.get("hsn_sac", old["hsn_sac"]),
                body.get("busy_item_id", old["busy_item_id"]),
                1 if body.get("is_active", True) else 0,
                product_id
            ))

            log_audit(
                user_id=user_id, username=username, action="EDIT",
                entity_type="product", entity_id=str(product_id),
                before_state=old, after_state=body, notes=f"Updated product {body.get('name')}",
                conn=conn
            )

            self._send_json({"success": True, "message": "Product updated successfully."})

    def _delete_product(self, product_id: int, body: Dict[str, Any], user_id: int, username: str):
        reason = (body.get("reason") or "User deleted product").strip()
        with get_db() as conn:
            product = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())
            if not product:
                self._send_error("Product not found", 404)
                return
            conn.execute("""
                UPDATE products SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by_user_id = ?, deletion_reason = ?
                WHERE id = ?
            """, (user_id, reason, product_id))
            log_audit(
                user_id=user_id, username=username, action="DELETE",
                entity_type="product", entity_id=str(product_id),
                before_state=product, notes=f"Deleted product {product['name']}: {reason}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Product '{product['name']}' deleted. You can restore it anytime from Deleted Items.", "product_id": product_id})

    def _restore_product(self, product_id: int, user_id: int, username: str):
        with get_db() as conn:
            product = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())
            if not product:
                self._send_error("Product not found", 404)
                return
            conn.execute("""
                UPDATE products SET is_deleted = 0, deleted_at = NULL, deleted_by_user_id = NULL, deletion_reason = NULL
                WHERE id = ?
            """, (product_id,))
            log_audit(
                user_id=user_id, username=username, action="RESTORE",
                entity_type="product", entity_id=str(product_id),
                after_state={"is_deleted": 0}, notes=f"Restored product {product['name']}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Product '{product['name']}' restored successfully.", "product_id": product_id})

    # =========================================================================
    # DEALS & DEAL CHAIN WORKFLOWS
    # =========================================================================

    def _create_initial_deal(self, body: Dict[str, Any], user_id: int, username: str):
        is_valid, err = validate_deal_data(body, is_resale=False)
        if not is_valid:
            self._send_error(err)
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Generate new Chain Code: CHN-YYYY-XXXX
            year_str = datetime.now().strftime("%Y")
            max_chain = cursor.execute("SELECT COUNT(*) FROM deal_chains").fetchone()[0]
            chain_code = f"CHN-{year_str}-{(max_chain + 1):04d}"

            max_deal = cursor.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
            deal_number = f"DL-{year_str}-{(max_deal + 1):04d}"

            # Calculate financial parameters
            summary = compute_deal_summary(body)
            deal_date_iso = parse_date_to_iso(body.get("deal_date")) or datetime.now().strftime("%Y-%m-%d")
            delivery_date_iso = parse_date_to_iso(body.get("delivery_date")) or deal_date_iso

            # Create Chain record
            cursor.execute("""
                INSERT INTO deal_chains (
                    chain_code, product_id, initial_quantity_qtl, remaining_quantity_qtl,
                    original_bill_seller_id, final_bill_buyer_id, final_billing_rate,
                    status, notes, created_by_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'in_progress', ?, ?)
            """, (
                chain_code,
                body["product_id"],
                float(summary["quantity_qtl"]),
                float(summary["quantity_qtl"]),
                body["buyer_id"],   # Root Lot Purchase Buyer issues the final direct bill
                body["buyer_id"],   # Initial Buyer
                float(summary["rate_per_qtl"]),
                body.get("notes"),
                user_id
            ))
            chain_id = cursor.lastrowid

            # Create Initial Deal
            cursor.execute("""
                INSERT INTO deals (
                    deal_number, chain_id, parent_deal_id, deal_date, instruction_date,
                    buyer_id, seller_id, product_id, quantity_qtl, quantity_tonnes,
                    rate_per_qtl, gst_applicable, gst_pct, is_rate_gst_inclusive,
                    taxable_rate_per_qtl, taxable_value, gst_amount, total_value,
                    authorized_rate_per_qtl, actual_rate_per_qtl, price_diff_per_qtl, price_diff_profit,
                    buyer_brokerage_rate_per_tonne, buyer_brokerage_amount,
                    seller_brokerage_rate_per_tonne, seller_brokerage_amount,
                    total_brokerage, total_deal_earning, delivery_date, status,
                    brokerage_override_reason, notes, created_by_user_id
                ) VALUES (
                    ?, ?, NULL, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    0.0, ?, 0.0, 0.0,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                deal_number, chain_id, deal_date_iso, deal_date_iso,
                body["buyer_id"], body["seller_id"], body["product_id"],
                float(summary["quantity_qtl"]), float(summary["quantity_tonnes"]),
                float(summary["rate_per_qtl"]), 1 if body.get("gst_applicable", True) else 0,
                float(body.get("gst_pct", 5.0)), 1 if body.get("is_rate_gst_inclusive", False) else 0,
                float(summary["rate_per_qtl"]), float(summary["taxable_value"]), float(summary["gst_amount"]), float(summary["total_value"]),
                float(summary["rate_per_qtl"]),
                float(summary["buyer_brokerage_rate_per_tonne"]), float(summary["buyer_brokerage_amount"]),
                float(summary["seller_brokerage_rate_per_tonne"]), float(summary["seller_brokerage_amount"]),
                float(summary["total_brokerage"]), float(summary["total_deal_earning"]),
                delivery_date_iso, body.get("status", "confirmed"),
                body.get("brokerage_override_reason"), body.get("notes"), user_id
            ))
            deal_id = cursor.lastrowid

            log_audit(
                user_id=user_id, username=username, action="CREATE",
                entity_type="deal", entity_id=str(deal_id),
                after_state=body, notes=f"Created initial deal {deal_number} in chain {chain_code}",
                conn=conn
            )

            self._send_json({
                "success": True,
                "deal_id": deal_id,
                "chain_id": chain_id,
                "deal_number": deal_number,
                "chain_code": chain_code,
                "summary": summary
            })

    def _add_chain_resale(self, chain_id: int, body: Dict[str, Any], user_id: int, username: str):
        """
        Creates next resale link in an active chain:
        1. Previous buyer acts as instructing seller.
        2. Validates remaining quantity (prevents overselling).
        3. Computes price-diff profit = (actual_sale_rate - authorized_rate) * quantity_in_quintals.
        4. Calculates buyer & seller brokerage per metric tonne.
        5. Updates chain's final buyer and direct billing instruction.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            chain = row_to_dict(cursor.execute("SELECT * FROM deal_chains WHERE id = ?", (chain_id,)).fetchone())
            if not chain:
                self._send_error("Deal chain not found", 404)
                return

            if chain["status"] in ("billed", "cancelled"):
                self._send_error(f"Cannot add resale link to chain with status '{chain['status']}'")
                return

            # Get parent/latest deal in this chain
            latest_deal = row_to_dict(cursor.execute("""
                SELECT * FROM deals WHERE chain_id = ? AND status != 'cancelled' ORDER BY id DESC LIMIT 1
            """, (chain_id,)).fetchone())

            if not latest_deal:
                self._send_error("No active prior deal in chain.")
                return

            # Instructing seller defaults to the previous buyer
            seller_id = body.get("seller_id") or latest_deal["buyer_id"]
            buyer_id = body.get("buyer_id")
            product_id = chain["product_id"]

            body["seller_id"] = seller_id
            body["product_id"] = product_id

            is_valid, err = validate_deal_data(body, is_resale=True)
            if not is_valid:
                self._send_error(err)
                return

            # Quantity check against remaining available balance
            qty_qtl = to_decimal(body.get("quantity_qtl", latest_deal["quantity_qtl"]))
            remaining_qtl = to_decimal(chain["remaining_quantity_qtl"])

            if qty_qtl > remaining_qtl:
                self._send_error(f"Resale quantity ({qty_qtl:g} Qtl) exceeds available chain balance ({remaining_qtl:g} Qtl).")
                return

            # Generate Deal Number
            year_str = datetime.now().strftime("%Y")
            max_deal = cursor.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
            deal_number = f"DL-{year_str}-{(max_deal + 1):04d}"

            # Calculate deal figures
            body["quantity_qtl"] = float(qty_qtl)
            summary = compute_deal_summary(body)

            instruction_date_iso = parse_date_to_iso(body.get("instruction_date")) or datetime.now().strftime("%Y-%m-%d")
            deal_date_iso = parse_date_to_iso(body.get("deal_date")) or instruction_date_iso
            delivery_date_iso = parse_date_to_iso(body.get("delivery_date")) or latest_deal["delivery_date"]

            cursor.execute("""
                INSERT INTO deals (
                    deal_number, chain_id, parent_deal_id, deal_date, instruction_date,
                    buyer_id, seller_id, product_id, quantity_qtl, quantity_tonnes,
                    rate_per_qtl, gst_applicable, gst_pct, is_rate_gst_inclusive,
                    taxable_rate_per_qtl, taxable_value, gst_amount, total_value,
                    authorized_rate_per_qtl, actual_rate_per_qtl, price_diff_per_qtl, price_diff_profit,
                    buyer_brokerage_rate_per_tonne, buyer_brokerage_amount,
                    seller_brokerage_rate_per_tonne, seller_brokerage_amount,
                    total_brokerage, total_deal_earning, delivery_date, status,
                    brokerage_override_reason, notes, created_by_user_id
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?, 'confirmed',
                    ?, ?, ?
                )
            """, (
                deal_number, chain_id, latest_deal["id"], deal_date_iso, instruction_date_iso,
                buyer_id, seller_id, product_id,
                float(summary["quantity_qtl"]), float(summary["quantity_tonnes"]),
                float(summary["actual_rate_per_qtl"]), 1 if body.get("gst_applicable", True) else 0,
                float(body.get("gst_pct", 5.0)), 1 if body.get("is_rate_gst_inclusive", False) else 0,
                float(summary["actual_rate_per_qtl"]), float(summary["taxable_value"]), float(summary["gst_amount"]), float(summary["total_value"]),
                float(summary["authorized_rate_per_qtl"]), float(summary["actual_rate_per_qtl"]),
                float(summary["price_diff_per_qtl"]), float(summary["price_diff_profit"]),
                float(summary["buyer_brokerage_rate_per_tonne"]), float(summary["buyer_brokerage_amount"]),
                float(summary["seller_brokerage_rate_per_tonne"]), float(summary["seller_brokerage_amount"]),
                float(summary["total_brokerage"]), float(summary["total_deal_earning"]),
                delivery_date_iso, body.get("brokerage_override_reason"), body.get("notes"), user_id
            ))
            new_deal_id = cursor.lastrowid

            # Update chain status & final buyer
            cursor.execute("""
                UPDATE deal_chains SET
                    final_bill_buyer_id = ?,
                    final_billing_rate = ?,
                    status = 'ready_for_billing',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (buyer_id, float(summary["actual_rate_per_qtl"]), chain_id))

            log_audit(
                user_id=user_id, username=username, action="CREATE",
                entity_type="deal", entity_id=str(new_deal_id),
                after_state=body,
                notes=f"Added resale deal {deal_number} to chain {chain['chain_code']} (Profit: ₹{summary['price_diff_profit']})",
                conn=conn
            )

            self._send_json({
                "success": True,
                "deal_id": new_deal_id,
                "deal_number": deal_number,
                "chain_id": chain_id,
                "summary": summary
            })

    def _cancel_deal(self, deal_id: int, body: Dict[str, Any], user_id: int, username: str):
        reason = (body.get("reason") or "").strip()
        if not reason:
            self._send_error("Mandatory cancellation reason must be provided.")
            return

        with get_db() as conn:
            deal = row_to_dict(conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone())
            if not deal:
                self._send_error("Deal not found", 404)
                return

            if deal["status"] == "cancelled":
                self._send_error("Deal is already cancelled.")
                return

            conn.execute("""
                UPDATE deals SET
                    status = 'cancelled',
                    cancellation_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (reason, deal_id))

            log_audit(
                user_id=user_id, username=username, action="CANCEL",
                entity_type="deal", entity_id=str(deal_id),
                before_state=deal, after_state={"status": "cancelled", "reason": reason},
                notes=f"Cancelled deal {deal['deal_number']}. Reason: {reason}",
                conn=conn
            )

            self._send_json({"success": True, "message": "Deal cancelled successfully."})

    def _delete_deal(self, deal_id: int, body: Dict[str, Any], user_id: int, username: str):
        reason = (body.get("reason") or "User deleted deal").strip()
        with get_db() as conn:
            deal = row_to_dict(conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone())
            if not deal:
                self._send_error("Deal not found", 404)
                return
            conn.execute("""
                UPDATE deals SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by_user_id = ?, deletion_reason = ?
                WHERE id = ?
            """, (user_id, reason, deal_id))

            log_audit(
                user_id=user_id, username=username, action="DELETE",
                entity_type="deal", entity_id=str(deal_id),
                before_state=deal, notes=f"Deleted deal {deal['deal_number']}: {reason}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Deal {deal['deal_number']} deleted. You can restore it anytime from Deleted Items.", "deal_id": deal_id})

    def _restore_deal(self, deal_id: int, user_id: int, username: str):
        with get_db() as conn:
            deal = row_to_dict(conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone())
            if not deal:
                self._send_error("Deal not found", 404)
                return
            conn.execute("""
                UPDATE deals SET is_deleted = 0, deleted_at = NULL, deleted_by_user_id = NULL, deletion_reason = NULL
                WHERE id = ?
            """, (deal_id,))
            # Also ensure chain is not marked deleted
            conn.execute("UPDATE deal_chains SET is_deleted = 0 WHERE id = ?", (deal["chain_id"],))

            log_audit(
                user_id=user_id, username=username, action="RESTORE",
                entity_type="deal", entity_id=str(deal_id),
                after_state={"is_deleted": 0}, notes=f"Restored deal {deal['deal_number']}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Deal {deal['deal_number']} restored successfully.", "deal_id": deal_id})

    def _delete_chain(self, chain_id: int, body: Dict[str, Any], user_id: int, username: str):
        reason = (body.get("reason") or "User deleted entire chain").strip()
        with get_db() as conn:
            chain = row_to_dict(conn.execute("SELECT * FROM deal_chains WHERE id = ?", (chain_id,)).fetchone())
            if not chain:
                self._send_error("Deal chain not found", 404)
                return
            # Delete chain and all its deals
            conn.execute("""
                UPDATE deal_chains SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by_user_id = ?, deletion_reason = ?
                WHERE id = ?
            """, (user_id, reason, chain_id))
            conn.execute("""
                UPDATE deals SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by_user_id = ?, deletion_reason = ?
                WHERE chain_id = ?
            """, (user_id, f"Cascade from chain {chain['chain_code']}: {reason}", chain_id))

            log_audit(
                user_id=user_id, username=username, action="DELETE",
                entity_type="deal_chain", entity_id=str(chain_id),
                before_state=chain, notes=f"Deleted chain {chain['chain_code']}: {reason}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Deal chain {chain['chain_code']} and all associated deals deleted. You can restore it anytime from Deleted Items.", "chain_id": chain_id})

    def _restore_chain(self, chain_id: int, user_id: int, username: str):
        with get_db() as conn:
            chain = row_to_dict(conn.execute("SELECT * FROM deal_chains WHERE id = ?", (chain_id,)).fetchone())
            if not chain:
                self._send_error("Deal chain not found", 404)
                return
            conn.execute("""
                UPDATE deal_chains SET is_deleted = 0, deleted_at = NULL, deleted_by_user_id = NULL, deletion_reason = NULL
                WHERE id = ?
            """, (chain_id,))
            conn.execute("""
                UPDATE deals SET is_deleted = 0, deleted_at = NULL, deleted_by_user_id = NULL, deletion_reason = NULL
                WHERE chain_id = ?
            """, (chain_id,))

            log_audit(
                user_id=user_id, username=username, action="RESTORE",
                entity_type="deal_chain", entity_id=str(chain_id),
                after_state={"is_deleted": 0}, notes=f"Restored chain {chain['chain_code']}",
                conn=conn
            )
            self._send_json({"success": True, "message": f"Deal chain {chain['chain_code']} and deals restored successfully.", "chain_id": chain_id})

    def _update_deal(self, deal_id: int, body: Dict[str, Any], user_id: int, username: str):
        with get_db() as conn:
            old = row_to_dict(conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone())
            if not old:
                self._send_error("Deal not found", 404)
                return

            if old["status"] == "cancelled":
                self._send_error("Cannot edit a cancelled deal.")
                return

            # Recompute summary
            summary = compute_deal_summary(body)
            deal_date_iso = parse_date_to_iso(body.get("deal_date")) or old["deal_date"]
            delivery_date_iso = parse_date_to_iso(body.get("delivery_date")) or old["delivery_date"]

            conn.execute("""
                UPDATE deals SET
                    deal_date = ?, instruction_date = ?,
                    buyer_id = ?, seller_id = ?, product_id = ?,
                    quantity_qtl = ?, quantity_tonnes = ?,
                    rate_per_qtl = ?, gst_applicable = ?, gst_pct = ?,
                    taxable_value = ?, gst_amount = ?, total_value = ?,
                    authorized_rate_per_qtl = ?, actual_rate_per_qtl = ?,
                    price_diff_per_qtl = ?, price_diff_profit = ?,
                    buyer_brokerage_rate_per_tonne = ?, buyer_brokerage_amount = ?,
                    seller_brokerage_rate_per_tonne = ?, seller_brokerage_amount = ?,
                    total_brokerage = ?, total_deal_earning = ?,
                    delivery_date = ?, brokerage_override_reason = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                deal_date_iso, body.get("instruction_date", old["instruction_date"]),
                body.get("buyer_id", old["buyer_id"]), body.get("seller_id", old["seller_id"]),
                body.get("product_id", old["product_id"]),
                float(summary["quantity_qtl"]), float(summary["quantity_tonnes"]),
                float(summary["actual_rate_per_qtl"]), 1 if body.get("gst_applicable", True) else 0,
                float(body.get("gst_pct", 5.0)),
                float(summary["taxable_value"]), float(summary["gst_amount"]), float(summary["total_value"]),
                float(summary["authorized_rate_per_qtl"]), float(summary["actual_rate_per_qtl"]),
                float(summary["price_diff_per_qtl"]), float(summary["price_diff_profit"]),
                float(summary["buyer_brokerage_rate_per_tonne"]), float(summary["buyer_brokerage_amount"]),
                float(summary["seller_brokerage_rate_per_tonne"]), float(summary["seller_brokerage_amount"]),
                float(summary["total_brokerage"]), float(summary["total_deal_earning"]),
                delivery_date_iso, body.get("brokerage_override_reason", old["brokerage_override_reason"]),
                body.get("notes", old["notes"]), deal_id
            ))

            log_audit(
                user_id=user_id, username=username, action="EDIT",
                entity_type="deal", entity_id=str(deal_id),
                before_state=old, after_state=body,
                notes=f"Edited deal {old['deal_number']}. Reason: {body.get('edit_reason', 'Routine update')}",
                conn=conn
            )

            self._send_json({"success": True, "message": "Deal updated successfully."})

    def _approve_chain_billing(self, chain_id: int, body: Dict[str, Any], user_id: int, username: str):
        with get_db() as conn:
            chain = row_to_dict(conn.execute("SELECT * FROM deal_chains WHERE id = ?", (chain_id,)).fetchone())
            if not chain:
                self._send_error("Chain not found", 404)
                return

            conn.execute("""
                UPDATE deal_chains SET
                    status = 'billed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (chain_id,))

            conn.execute("""
                UPDATE deals SET
                    status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE chain_id = ? AND status != 'cancelled'
            """, (chain_id,))

            log_audit(
                user_id=user_id, username=username, action="APPROVE",
                entity_type="deal_chain", entity_id=str(chain_id),
                notes=f"Approved official direct billing instruction for chain {chain['chain_code']} (Moved from active workbench to billed register)",
                conn=conn
            )

            self._send_json({"success": True, "message": "Official Direct Billing approved. Transactions moved to completed register."})

    def _get_deals(self, query: Dict[str, List[str]]):
        with get_db() as conn:
            sql = """
                SELECT d.*,
                       b.name as buyer_name, b.city as buyer_city,
                       s.name as seller_name, s.city as seller_city,
                       p.name as product_name, p.code as product_code,
                       c.chain_code,
                       u.full_name as creator_name
                FROM deals d
                JOIN parties b ON d.buyer_id = b.id
                JOIN parties s ON d.seller_id = s.id
                JOIN products p ON d.product_id = p.id
                JOIN deal_chains c ON d.chain_id = c.id
                LEFT JOIN users u ON d.created_by_user_id = u.id
                WHERE COALESCE(d.is_deleted, 0) = 0
            """
            params = []

            # Filters
            if "status" in query and query["status"][0]:
                sql += " AND d.status = ?"
                params.append(query["status"][0])
            if "party_id" in query and query["party_id"][0]:
                sql += " AND (d.buyer_id = ? OR d.seller_id = ?)"
                params.extend([query["party_id"][0], query["party_id"][0]])
            if "product_id" in query and query["product_id"][0]:
                sql += " AND d.product_id = ?"
                params.append(query["product_id"][0])
            if "chain_id" in query and query["chain_id"][0]:
                sql += " AND d.chain_id = ?"
                params.append(query["chain_id"][0])
            if "from_date" in query and query["from_date"][0]:
                sql += " AND d.deal_date >= ?"
                params.append(parse_date_to_iso(query["from_date"][0]))
            if "to_date" in query and query["to_date"][0]:
                sql += " AND d.deal_date <= ?"
                params.append(parse_date_to_iso(query["to_date"][0]))

            sql += " ORDER BY d.deal_date DESC, d.id DESC"
            rows = conn.execute(sql, params).fetchall()
            self._send_json({"success": True, "deals": rows_to_dict_list(rows)})

    def _get_deal_detail(self, deal_id: int):
        with get_db() as conn:
            deal = row_to_dict(conn.execute("""
                SELECT d.*,
                       b.name as buyer_name, b.city as buyer_city, b.gstin as buyer_gstin,
                       s.name as seller_name, s.city as seller_city, s.gstin as seller_gstin,
                       p.name as product_name, p.code as product_code,
                       c.chain_code
                FROM deals d
                JOIN parties b ON d.buyer_id = b.id
                JOIN parties s ON d.seller_id = s.id
                JOIN products p ON d.product_id = p.id
                JOIN deal_chains c ON d.chain_id = c.id
                WHERE d.id = ? AND COALESCE(d.is_deleted, 0) = 0
            """, (deal_id,)).fetchone())

            if not deal:
                self._send_error("Deal not found", 404)
                return

            self._send_json({"success": True, "deal": deal})

    def _get_chains(self, query: Dict[str, List[str]]):
        with get_db() as conn:
            sql = """
                SELECT c.*, p.name as product_name, p.code as product_code,
                       obs.name as original_bill_seller_name,
                       fbb.name as final_bill_buyer_name,
                       (SELECT COUNT(*) FROM deals WHERE chain_id = c.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as deal_count,
                       (SELECT COALESCE(SUM(price_diff_profit), 0) FROM deals WHERE chain_id = c.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as total_price_diff_profit,
                       (SELECT COALESCE(SUM(total_brokerage), 0) FROM deals WHERE chain_id = c.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as total_brokerage,
                       (SELECT COALESCE(SUM(total_deal_earning), 0) FROM deals WHERE chain_id = c.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as total_chain_earning
                FROM deal_chains c
                JOIN products p ON c.product_id = p.id
                LEFT JOIN parties obs ON c.original_bill_seller_id = obs.id
                LEFT JOIN parties fbb ON c.final_bill_buyer_id = fbb.id
                WHERE COALESCE(c.is_deleted, 0) = 0
            """
            params = []
            if "status" in query and query["status"][0]:
                sql += " AND c.status = ?"
                params.append(query["status"][0])

            sql += " ORDER BY c.id DESC"
            rows = conn.execute(sql, params).fetchall()

            chains_list = []
            for r in rows:
                ch = dict(r)
                seller_name = ch.get("original_bill_seller_name") or "Original Seller"
                buyer_name = ch.get("final_bill_buyer_name") or "Final Buyer"
                qty = ch.get("remaining_quantity_qtl", ch.get("initial_quantity_qtl", 0))
                rate = ch.get("final_billing_rate", 0)
                p_code = ch.get("product_code", "M.OIL")
                ch["direct_billing_instruction"] = f"{seller_name} will issue a direct bill to {buyer_name} for {qty:g} quintals of {p_code} at ₹{rate:,.2f} + GST per quintal."
                chains_list.append(ch)

            self._send_json({"success": True, "chains": chains_list})

    def _get_chain_detail(self, chain_id: int):
        with get_db() as conn:
            chain = row_to_dict(conn.execute("""
                SELECT c.*, p.name as product_name, p.code as product_code,
                       obs.name as original_bill_seller_name,
                       fbb.name as final_bill_buyer_name
                FROM deal_chains c
                JOIN products p ON c.product_id = p.id
                LEFT JOIN parties obs ON c.original_bill_seller_id = obs.id
                LEFT JOIN parties fbb ON c.final_bill_buyer_id = fbb.id
                WHERE c.id = ? AND COALESCE(c.is_deleted, 0) = 0
            """, (chain_id,)).fetchone())

            if not chain:
                self._send_error("Chain not found", 404)
                return

            deals_rows = conn.execute("""
                SELECT d.*,
                       b.name as buyer_name, b.city as buyer_city,
                       s.name as seller_name, s.city as seller_city,
                       p.name as product_name, p.code as product_code,
                       u.full_name as creator_name
                FROM deals d
                JOIN parties b ON d.buyer_id = b.id
                JOIN parties s ON d.seller_id = s.id
                JOIN products p ON d.product_id = p.id
                LEFT JOIN users u ON d.created_by_user_id = u.id
                WHERE d.chain_id = ? AND COALESCE(d.is_deleted, 0) = 0
                ORDER BY d.deal_date ASC, d.id ASC
            """, (chain_id,)).fetchall()

            deals = rows_to_dict_list(deals_rows)
            chain_totals = compute_chain_totals(deals)

            self._send_json({
                "success": True,
                "chain": chain,
                "deals": deals,
                "chain_totals": chain_totals
            })

    def _get_deleted_items(self, query: Dict[str, List[str]]):
        """Returns all soft-deleted records across deals, chains, parties, products, payments."""
        item_type = query.get("type", ["all"])[0]
        with get_db() as conn:
            deleted_items = []

            # 1. Deleted Deals
            if item_type in ("all", "deals"):
                rows = conn.execute("""
                    SELECT d.id, d.deal_number, d.deal_date, d.quantity_qtl, d.rate_per_qtl,
                           d.price_diff_profit, d.total_brokerage, d.deleted_at, d.deletion_reason,
                           b.name as buyer_name, s.name as seller_name, p.name as product_name,
                           u.full_name as deleted_by_name
                    FROM deals d
                    JOIN parties b ON d.buyer_id = b.id
                    JOIN parties s ON d.seller_id = s.id
                    JOIN products p ON d.product_id = p.id
                    LEFT JOIN users u ON d.deleted_by_user_id = u.id
                    WHERE d.is_deleted = 1
                    ORDER BY d.deleted_at DESC
                """).fetchall()
                for r in rows:
                    deleted_items.append({
                        "entity_type": "deal",
                        "id": r["id"],
                        "title": f"Deal {r['deal_number']}",
                        "badge": r["product_name"],
                        "summary": f"Buyer: {r['buyer_name']} | Seller: {r['seller_name']} | Qty: {r['quantity_qtl']:g} Qtl @ ₹{r['rate_per_qtl']:,.2f}",
                        "financial_impact": f"Profit: ₹{r['price_diff_profit']:,.2f} | Brok: ₹{r['total_brokerage']:,.2f}",
                        "deleted_at": r["deleted_at"],
                        "deleted_by": r["deleted_by_name"] or "User",
                        "deletion_reason": r["deletion_reason"] or "Deleted"
                    })

            # 2. Deleted Chains
            if item_type in ("all", "chains"):
                rows = conn.execute("""
                    SELECT c.id, c.chain_code, c.initial_quantity_qtl, c.deleted_at, c.deletion_reason,
                           p.name as product_name, u.full_name as deleted_by_name
                    FROM deal_chains c
                    JOIN products p ON c.product_id = p.id
                    LEFT JOIN users u ON c.deleted_by_user_id = u.id
                    WHERE c.is_deleted = 1
                    ORDER BY c.deleted_at DESC
                """).fetchall()
                for r in rows:
                    deleted_items.append({
                        "entity_type": "chain",
                        "id": r["id"],
                        "title": f"Deal Chain {r['chain_code']}",
                        "badge": r["product_name"],
                        "summary": f"Lot Size: {r['initial_quantity_qtl']:g} Quintals",
                        "financial_impact": "Includes all chain deal links",
                        "deleted_at": r["deleted_at"],
                        "deleted_by": r["deleted_by_name"] or "User",
                        "deletion_reason": r["deletion_reason"] or "Deleted"
                    })

            # 3. Deleted Parties
            if item_type in ("all", "parties"):
                rows = conn.execute("""
                    SELECT p.id, p.name, p.city, p.party_type, p.deleted_at, p.deletion_reason,
                           u.full_name as deleted_by_name
                    FROM parties p
                    LEFT JOIN users u ON p.deleted_by_user_id = u.id
                    WHERE p.is_deleted = 1
                    ORDER BY p.deleted_at DESC
                """).fetchall()
                for r in rows:
                    deleted_items.append({
                        "entity_type": "party",
                        "id": r["id"],
                        "title": f"Party: {r['name']}",
                        "badge": r["party_type"].upper(),
                        "summary": f"City: {r['city'] or 'India'}",
                        "financial_impact": "Party Master profile",
                        "deleted_at": r["deleted_at"],
                        "deleted_by": r["deleted_by_name"] or "User",
                        "deletion_reason": r["deletion_reason"] or "Deleted"
                    })

            # 4. Deleted Products
            if item_type in ("all", "products"):
                rows = conn.execute("""
                    SELECT pr.id, pr.name, pr.code, pr.deleted_at, pr.deletion_reason,
                           u.full_name as deleted_by_name
                    FROM products pr
                    LEFT JOIN users u ON pr.deleted_by_user_id = u.id
                    WHERE pr.is_deleted = 1
                    ORDER BY pr.deleted_at DESC
                """).fetchall()
                for r in rows:
                    deleted_items.append({
                        "entity_type": "product",
                        "id": r["id"],
                        "title": f"Product: {r['name']}",
                        "badge": r["code"],
                        "summary": f"Code: {r['code']}",
                        "financial_impact": "Edible Oil Product Master",
                        "deleted_at": r["deleted_at"],
                        "deleted_by": r["deleted_by_name"] or "User",
                        "deletion_reason": r["deletion_reason"] or "Deleted"
                    })

            # 5. Deleted Payments
            if item_type in ("all", "payments"):
                rows = conn.execute("""
                    SELECT pm.id, pm.amount, pm.payment_date, pm.payment_type, pm.reference_number,
                           pm.deleted_at, pm.deletion_reason, p.name as party_name,
                           u.full_name as deleted_by_name
                    FROM brokerage_payments pm
                    JOIN parties p ON pm.party_id = p.id
                    LEFT JOIN users u ON pm.deleted_by_user_id = u.id
                    WHERE pm.is_deleted = 1
                    ORDER BY pm.deleted_at DESC
                """).fetchall()
                for r in rows:
                    deleted_items.append({
                        "entity_type": "payment",
                        "id": r["id"],
                        "title": f"Brokerage Payment ₹{r['amount']:,.2f}",
                        "badge": r["payment_type"].upper(),
                        "summary": f"Party: {r['party_name']} | Ref: {r['reference_number'] or 'N/A'}",
                        "financial_impact": f"Amount: ₹{r['amount']:,.2f}",
                        "deleted_at": r["deleted_at"],
                        "deleted_by": r["deleted_by_name"] or "User",
                        "deletion_reason": r["deletion_reason"] or "Deleted"
                    })

            deleted_items.sort(key=lambda x: x.get("deleted_at") or "", reverse=True)
            self._send_json({"success": True, "deleted_items": deleted_items, "total_count": len(deleted_items)})

    def _get_report_data(self, report_type: str, query: Dict[str, List[str]]):
        with get_db() as conn:
            # Multi-parameter report queries
            from_date = parse_date_to_iso(query.get("from_date", [None])[0])
            to_date = parse_date_to_iso(query.get("to_date", [None])[0])
            party_id = query.get("party_id", [None])[0]
            product_id = query.get("product_id", [None])[0]

            if report_type in ("deals", "price_diff", "buyer_brokerage", "seller_brokerage", "earnings", "pending_deliveries", "cancelled"):
                sql = """
                    SELECT d.*, b.name as buyer_name, s.name as seller_name,
                           p.name as product_name, p.code as product_code, c.chain_code
                    FROM deals d
                    JOIN parties b ON d.buyer_id = b.id
                    JOIN parties s ON d.seller_id = s.id
                    JOIN products p ON d.product_id = p.id
                    JOIN deal_chains c ON d.chain_id = c.id
                    WHERE COALESCE(d.is_deleted, 0) = 0
                """
                params = []
                if from_date:
                    sql += " AND d.deal_date >= ?"
                    params.append(from_date)
                if to_date:
                    sql += " AND d.deal_date <= ?"
                    params.append(to_date)
                if party_id:
                    sql += " AND (d.buyer_id = ? OR d.seller_id = ?)"
                    params.extend([party_id, party_id])
                if product_id:
                    sql += " AND d.product_id = ?"
                    params.append(product_id)

                if report_type == "cancelled":
                    sql += " AND d.status = 'cancelled'"
                elif report_type == "pending_deliveries":
                    sql += " AND d.status = 'confirmed' AND d.delivery_date >= date('now')"
                else:
                    sql += " AND d.status != 'cancelled'"

                sql += " ORDER BY d.deal_date DESC, d.id DESC"
                rows = conn.execute(sql, params).fetchall()
                self._send_json({"success": True, "report_type": report_type, "rows": rows_to_dict_list(rows)})
                return

            elif report_type == "party_outstanding":
                rows = conn.execute("""
                    SELECT p.id, p.name, p.party_type, p.city, p.gstin,
                           COALESCE(SUM(d.buyer_brokerage_amount), 0) + COALESCE(SUM(d2.seller_brokerage_amount), 0) as total_brokerage_charged,
                           COALESCE((SELECT SUM(amount) FROM brokerage_payments WHERE party_id = p.id AND COALESCE(is_deleted, 0) = 0), 0) as total_brokerage_paid
                    FROM parties p
                    LEFT JOIN deals d ON d.buyer_id = p.id AND d.status != 'cancelled' AND COALESCE(d.is_deleted, 0) = 0
                    LEFT JOIN deals d2 ON d2.seller_id = p.id AND d2.status != 'cancelled' AND COALESCE(d2.is_deleted, 0) = 0
                    WHERE COALESCE(p.is_deleted, 0) = 0
                    GROUP BY p.id
                    ORDER BY (total_brokerage_charged - total_brokerage_paid) DESC
                """).fetchall()

                result = []
                for r in rows:
                    item = dict(r)
                    item["outstanding_brokerage"] = item["total_brokerage_charged"] - item["total_brokerage_paid"]
                    result.append(item)

                self._send_json({"success": True, "report_type": report_type, "rows": result})
                return

            self._send_error(f"Unknown report type: {report_type}")

    def _export_excel(self, query: Dict[str, List[str]], user: Optional[Dict[str, Any]]):
        with get_db() as conn:
            deals_rows = conn.execute("""
                SELECT d.*,
                       b.name as buyer_name, s.name as seller_name,
                       p.name as product_name, p.code as product_code,
                       c.chain_code,
                       obs.name as original_bill_seller_name,
                       fbb.name as final_bill_buyer_name,
                       u.full_name as creator_name
                FROM deals d
                JOIN parties b ON d.buyer_id = b.id
                JOIN parties s ON d.seller_id = s.id
                JOIN products p ON d.product_id = p.id
                JOIN deal_chains c ON d.chain_id = c.id
                LEFT JOIN parties obs ON c.original_bill_seller_id = obs.id
                LEFT JOIN parties fbb ON c.final_bill_buyer_id = fbb.id
                LEFT JOIN users u ON d.created_by_user_id = u.id
                WHERE COALESCE(d.is_deleted, 0) = 0
                ORDER BY d.deal_date ASC, d.id ASC
            """).fetchall()
            deals = rows_to_dict_list(deals_rows)

            chains_rows = conn.execute("""
                SELECT c.*, p.name as product_name, p.code as product_code,
                       obs.name as original_bill_seller_name,
                       fbb.name as final_bill_buyer_name,
                       (SELECT COALESCE(SUM(price_diff_profit), 0) FROM deals WHERE chain_id = c.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as total_price_diff_profit,
                       (SELECT COALESCE(SUM(total_brokerage), 0) FROM deals WHERE chain_id = c.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as total_brokerage,
                       (SELECT COALESCE(SUM(total_deal_earning), 0) FROM deals WHERE chain_id = c.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0) as total_chain_earning
                FROM deal_chains c
                JOIN products p ON c.product_id = p.id
                LEFT JOIN parties obs ON c.original_bill_seller_id = obs.id
                LEFT JOIN parties fbb ON c.final_bill_buyer_id = fbb.id
                WHERE COALESCE(c.is_deleted, 0) = 0
            """).fetchall()

            chains = []
            for r in chains_rows:
                c = dict(r)
                seller = c.get("original_bill_seller_name") or "Original Seller"
                buyer = c.get("final_bill_buyer_name") or "Final Buyer"
                c["direct_billing_instruction"] = f"{seller} will issue a direct bill to {buyer} for {c.get('initial_quantity_qtl', 0):g} quintals of {c.get('product_code', 'M.OIL')} at ₹{c.get('final_billing_rate', 0):,.2f} + GST per quintal."
                chains.append(c)

            parties_rows = conn.execute("""
                SELECT p.*,
                       COALESCE((SELECT SUM(buyer_brokerage_amount) FROM deals WHERE buyer_id = p.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0), 0) +
                       COALESCE((SELECT SUM(seller_brokerage_amount) FROM deals WHERE seller_id = p.id AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0), 0) as total_brokerage_charged,
                       COALESCE((SELECT SUM(amount) FROM brokerage_payments WHERE party_id = p.id AND COALESCE(is_deleted, 0) = 0), 0) as total_brokerage_paid
                FROM parties p
                WHERE COALESCE(p.is_deleted, 0) = 0
            """).fetchall()

            parties = []
            for pr in parties_rows:
                p_dict = dict(pr)
                p_dict["outstanding_brokerage"] = p_dict["total_brokerage_charged"] - p_dict["total_brokerage_paid"]
                parties.append(p_dict)

            audit_rows = conn.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT 100").fetchall()
            audit_data = rows_to_dict_list(audit_rows)

            # Prevent duplicate export tracking & record version
            version_count = conn.execute("SELECT COUNT(*) FROM excel_exports").fetchone()[0] + 1
            filename = f"GNC_Brokerage_Register_v{version_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            conn.execute("""
                INSERT INTO excel_exports (
                    export_type, file_name, row_count, version_number, filters_applied, exported_by_user_id
                ) VALUES ('full_register', ?, ?, ?, ?, ?)
            """, (filename, len(deals), version_count, json.dumps(query), user["user_id"] if user else 1))

            log_audit(
                user_id=user["user_id"] if user else 1,
                username=user["username"] if user else "system",
                action="EXPORT",
                entity_type="excel",
                entity_id=str(version_count),
                notes=f"Exported Excel register v{version_count} with {len(deals)} deals",
                conn=conn
            )

            stream = create_excel_workbook(
                deals_data=deals,
                chains_data=chains,
                parties_data=parties,
                audit_data=audit_data,
                version=version_count,
                exported_by=user["full_name"] if user else "Administrator"
            )

            self._send_binary(stream.getvalue(), filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def _get_busy_mappings(self):
        with get_db() as conn:
            parties = conn.execute("SELECT id, name, busy_ledger_id FROM parties ORDER BY name ASC").fetchall()
            products = conn.execute("SELECT id, name, code, busy_item_id FROM products ORDER BY name ASC").fetchall()
            self._send_json({
                "success": True,
                "party_mappings": rows_to_dict_list(parties),
                "product_mappings": rows_to_dict_list(products)
            })

    def _get_busy_queue(self):
        with get_db() as conn:
            queue = conn.execute("""
                SELECT q.*, c.chain_code
                FROM busy_sync_queue q
                LEFT JOIN deal_chains c ON q.deal_chain_id = c.id
                ORDER BY q.id DESC LIMIT 50
            """).fetchall()
            self._send_json({"success": True, "queue": rows_to_dict_list(queue)})

    def _stage_busy_voucher(self, body: Dict[str, Any], user_id: int, username: str):
        chain_id = body.get("chain_id")
        deal_id = body.get("deal_id")
        voucher_type = body.get("voucher_type", "sales_direct_invoice")

        if voucher_type == "sales_direct_invoice":
            if not chain_id:
                self._send_error("Chain ID is required for direct sales invoice voucher.")
                return
            try:
                res = BusyAccountingAdapter.generate_direct_sales_voucher(int(chain_id))
            except Exception as e:
                self._send_error(str(e))
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO busy_sync_queue (
                        deal_chain_id, voucher_type, voucher_payload_json, status, approved_by_user_id
                    ) VALUES (?, 'Sales Invoice', ?, 'approved', ?)
                """, (chain_id, json.dumps(res), user_id))
                queue_id = cursor.lastrowid

                log_audit(
                    user_id=user_id, username=username, action="BUSY_SYNC",
                    entity_type="busy_voucher", entity_id=str(queue_id),
                    notes=f"Staged BUSY Direct Invoice Voucher for chain {chain_id}",
                    conn=conn
                )

                self._send_json({"success": True, "queue_id": queue_id, "voucher": res})
                return

        elif voucher_type == "brokerage_journal":
            if not deal_id:
                self._send_error("Deal ID is required for brokerage journal voucher.")
                return
            try:
                res = BusyAccountingAdapter.generate_brokerage_journal_voucher(int(deal_id))
            except Exception as e:
                self._send_error(str(e))
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO busy_sync_queue (
                        deal_chain_id, voucher_type, voucher_payload_json, status, approved_by_user_id
                    ) VALUES (NULL, 'Brokerage Journal', ?, 'approved', ?)
                """, (json.dumps(res), user_id))
                queue_id = cursor.lastrowid

                self._send_json({"success": True, "queue_id": queue_id, "voucher": res})
                return

        self._send_error("Invalid voucher type.")

    def _sync_busy_voucher(self, body: Dict[str, Any], user_id: int, username: str):
        queue_id = body.get("queue_id")
        if not queue_id:
            self._send_error("Queue ID required.")
            return

        with get_db() as conn:
            conn.execute("""
                UPDATE busy_sync_queue SET
                    status = 'posted',
                    external_reference = 'BUSY-VCH-' || hex(randomblob(4)),
                    synced_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (queue_id,))

            log_audit(
                user_id=user_id, username=username, action="BUSY_SYNC",
                entity_type="busy_queue", entity_id=str(queue_id),
                notes=f"Dispatched/Simulated BUSY voucher sync #{queue_id}",
                conn=conn
            )

            self._send_json({"success": True, "message": "Voucher posted/synchronized with BUSY adapter successfully."})

    def _undo_audit_event(self, event_id: int, user_id: int, username: str):
        with get_db() as conn:
            event = row_to_dict(conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone())
            if not event:
                self._send_error("Audit event not found.", 404)
                return

            action = event["action"]
            entity_type = event["entity_type"]
            entity_id = event["entity_id"]

            if action in ("DELETE", "CANCEL"):
                if entity_type == "deal":
                    deal = row_to_dict(conn.execute("SELECT * FROM deals WHERE id = ?", (entity_id,)).fetchone())
                    if not deal:
                        self._send_error("Target deal not found.", 404)
                        return
                    conn.execute("UPDATE deals SET is_deleted = 0, deleted_at = NULL, deletion_reason = NULL, status = CASE WHEN status = 'cancelled' THEN 'confirmed' ELSE status END, cancellation_reason = NULL WHERE id = ?", (entity_id,))
                    conn.execute("UPDATE deal_chains SET is_deleted = 0, deleted_at = NULL WHERE id = ?", (deal["chain_id"],))
                    log_audit(user_id=user_id, username=username, action="RESTORE", entity_type="deal", entity_id=str(entity_id), notes=f"Undid {action} step from Log #{event_id}", conn=conn)
                    self._send_json({"success": True, "message": f"Successfully reversed step and restored Deal {deal.get('deal_number', '#' + str(entity_id))}"})
                    return

                elif entity_type in ("deal_chain", "chain"):
                    chain = row_to_dict(conn.execute("SELECT * FROM deal_chains WHERE id = ?", (entity_id,)).fetchone())
                    conn.execute("UPDATE deal_chains SET is_deleted = 0, deleted_at = NULL, deletion_reason = NULL WHERE id = ?", (entity_id,))
                    conn.execute("UPDATE deals SET is_deleted = 0, deleted_at = NULL, deletion_reason = NULL WHERE chain_id = ?", (entity_id,))
                    log_audit(user_id=user_id, username=username, action="RESTORE", entity_type="chain", entity_id=str(entity_id), notes=f"Undid {action} step from Log #{event_id}", conn=conn)
                    chain_code = chain.get("chain_code") if chain else f"#{entity_id}"
                    self._send_json({"success": True, "message": f"Successfully reversed step and restored Chain {chain_code}"})
                    return

                elif entity_type == "party":
                    party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (entity_id,)).fetchone())
                    conn.execute("UPDATE parties SET is_deleted = 0, deleted_at = NULL, deletion_reason = NULL WHERE id = ?", (entity_id,))
                    log_audit(user_id=user_id, username=username, action="RESTORE", entity_type="party", entity_id=str(entity_id), notes=f"Undid {action} step from Log #{event_id}", conn=conn)
                    pname = party.get("name") if party else f"#{entity_id}"
                    self._send_json({"success": True, "message": f"Successfully reversed step and restored Party {pname}"})
                    return

                elif entity_type == "product":
                    prod = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (entity_id,)).fetchone())
                    conn.execute("UPDATE products SET is_deleted = 0, deleted_at = NULL, deletion_reason = NULL WHERE id = ?", (entity_id,))
                    log_audit(user_id=user_id, username=username, action="RESTORE", entity_type="product", entity_id=str(entity_id), notes=f"Undid {action} step from Log #{event_id}", conn=conn)
                    pname = prod.get("name") if prod else f"#{entity_id}"
                    self._send_json({"success": True, "message": f"Successfully reversed step and restored Product {pname}"})
                    return

                elif entity_type in ("brokerage_payment", "payment"):
                    conn.execute("UPDATE brokerage_payments SET is_deleted = 0, deleted_at = NULL, deletion_reason = NULL WHERE id = ?", (entity_id,))
                    log_audit(user_id=user_id, username=username, action="RESTORE", entity_type="payment", entity_id=str(entity_id), notes=f"Undid {action} step from Log #{event_id}", conn=conn)
                    self._send_json({"success": True, "message": f"Successfully reversed step and restored Payment receipt #{entity_id}"})
                    return

            self._send_error(f"Cannot automatically undo action '{action}' on '{entity_type}'.")

    # =========================================================================
    # ZERO-COST WHATSAPP & EMAIL COMMUNICATION HANDLERS
    # =========================================================================

    def _prepare_communication(self, body: Dict[str, Any]):
        """Prepares prefilled draft, resolves contact candidates, and checks privacy rules."""
        message_type = body.get("message_type", "custom_message")
        party_id = body.get("party_id")
        deal_id = body.get("deal_id")
        chain_id = body.get("chain_id")
        options = body.get("options", {})

        with get_db() as conn:
            party = None
            if party_id:
                party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (party_id,)).fetchone())

            deal = None
            if deal_id:
                deal = row_to_dict(conn.execute("""
                    SELECT d.*, b.name as buyer_name, s.name as seller_name, p.name as product_name, p.code as product_code
                    FROM deals d
                    JOIN parties b ON d.buyer_id = b.id
                    JOIN parties s ON d.seller_id = s.id
                    JOIN products p ON d.product_id = p.id
                    WHERE d.id = ?
                """, (deal_id,)).fetchone())
                if not party and deal:
                    # Auto-select party based on message type
                    target_party_id = deal.get("seller_id") if message_type == "deal_confirmation_seller" else deal.get("buyer_id")
                    party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (target_party_id,)).fetchone())
                    if not party:
                        party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (deal.get("seller_id") or deal.get("buyer_id"),)).fetchone())

            chain = None
            chain_totals = None
            if chain_id:
                chain = row_to_dict(conn.execute("""
                    SELECT c.*, p.name as product_name, p.code as product_code,
                           obs.name as original_bill_seller_name, fbb.name as final_bill_buyer_name
                    FROM deal_chains c
                    JOIN products p ON c.product_id = p.id
                    LEFT JOIN parties obs ON c.original_bill_seller_id = obs.id
                    LEFT JOIN parties fbb ON c.final_bill_buyer_id = fbb.id
                    WHERE c.id = ?
                """, (chain_id,)).fetchone())

                deals_rows = conn.execute("""
                    SELECT d.*, b.name as buyer_name, s.name as seller_name, p.name as product_name, p.code as product_code
                    FROM deals d
                    JOIN parties b ON d.buyer_id = b.id
                    JOIN parties s ON d.seller_id = s.id
                    JOIN products p ON d.product_id = p.id
                    WHERE d.chain_id = ? AND d.status != 'cancelled'
                    ORDER BY d.id ASC
                """, (chain_id,)).fetchall()
                if not deals_rows:
                    deals_rows = conn.execute("""
                        SELECT d.*, b.name as buyer_name, s.name as seller_name, p.name as product_name, p.code as product_code
                        FROM deals d
                        JOIN parties b ON d.buyer_id = b.id
                        JOIN parties s ON d.seller_id = s.id
                        JOIN products p ON d.product_id = p.id
                        WHERE d.chain_id = ?
                        ORDER BY d.id ASC
                    """, (chain_id,)).fetchall()

                if deals_rows:
                    chain_totals = compute_chain_totals(rows_to_dict_list(deals_rows))

                if not party and chain:
                    if chain.get("original_bill_seller_id"):
                        party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (chain["original_bill_seller_id"],)).fetchone())
                    elif chain_totals and chain_totals.get("original_bill_seller_id"):
                        party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (chain_totals["original_bill_seller_id"],)).fetchone())
                    elif chain.get("final_bill_buyer_id"):
                        party = row_to_dict(conn.execute("SELECT * FROM parties WHERE id = ?", (chain["final_bill_buyer_id"],)).fetchone())

            # Fallback party resolution if still None
            if not party:
                first_party = conn.execute("SELECT * FROM parties WHERE COALESCE(is_deleted, 0) = 0 ORDER BY id ASC LIMIT 1").fetchone()
                if not first_party:
                    first_party = conn.execute("SELECT * FROM parties ORDER BY id ASC LIMIT 1").fetchone()
                if first_party:
                    party = row_to_dict(first_party)
                else:
                    party = {
                        "id": 1,
                        "name": "Valued Client",
                        "contact_person": "Valued Client",
                        "phone": "",
                        "email": "",
                        "whatsapp_primary": "",
                        "email_primary": "",
                        "preferred_comm_method": "both"
                    }

            ledger = None
            if party and message_type in ("brokerage_statement", "brokerage_payment_reminder"):
                buyer_deals = conn.execute("""
                    SELECT buyer_brokerage_amount FROM deals WHERE buyer_id = ? AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0
                """, (party["id"],)).fetchall()
                seller_deals = conn.execute("""
                    SELECT seller_brokerage_amount FROM deals WHERE seller_id = ? AND status != 'cancelled' AND COALESCE(is_deleted, 0) = 0
                """, (party["id"],)).fetchall()
                buyer_side = sum(d["buyer_brokerage_amount"] for d in buyer_deals)
                seller_side = sum(d["seller_brokerage_amount"] for d in seller_deals)
                payments_for_party = conn.execute("""
                    SELECT amount FROM brokerage_payments WHERE party_id = ? AND COALESCE(is_deleted, 0) = 0
                """, (party["id"],)).fetchall()
                paid = sum(p["amount"] for p in payments_for_party)
                charged = buyer_side + seller_side
                ledger = {
                    "summary": {
                        "opening_balance": 0.0,
                        "buyer_side_brokerage": buyer_side,
                        "seller_side_brokerage": seller_side,
                        "total_brokerage_charged": charged,
                        "total_brokerage_paid": paid,
                        "outstanding_balance": charged - paid
                    }
                }

            all_parties_rows = conn.execute("SELECT id, name, contact_person, phone, email, whatsapp_primary, email_primary FROM parties WHERE COALESCE(is_deleted, 0) = 0 ORDER BY name ASC").fetchall()
            all_parties = rows_to_dict_list(all_parties_rows)

            draft = generate_communication_draft(
                message_type=message_type,
                party=party,
                deal=deal,
                chain=chain,
                chain_totals=chain_totals,
                ledger=ledger,
                options=options
            )
            draft["all_parties"] = all_parties

            self._send_json({"success": True, "draft": draft})

    def _log_communication(self, body: Dict[str, Any], user_id: int, username: str):
        """Logs a triggered communication draft with initial 'WhatsApp opened' or 'Email draft opened' status."""
        channel = body.get("channel", "whatsapp").lower()
        if channel not in ("whatsapp", "email"):
            self._send_error("Invalid communication channel. Must be 'whatsapp' or 'email'.")
            return

        recipient = (body.get("recipient_contact") or "").strip()
        if not recipient:
            self._send_error(f"Recipient {'phone number' if channel == 'whatsapp' else 'email address'} is required.")
            return

        if channel == "whatsapp":
            recipient = normalize_indian_phone(recipient)
            if not recipient:
                self._send_error("A valid WhatsApp number is required (91XXXXXXXXXX).")
                return
        elif channel == "email":
            if not validate_email(recipient):
                self._send_error("A valid recipient email address is required.")
                return

        party_id = body.get("party_id")
        party_name = body.get("party_name", "Client")
        contact_person = body.get("contact_person")
        deal_id = body.get("deal_id")
        chain_id = body.get("chain_id")
        message_type = body.get("message_type", "custom_message")
        subject = body.get("subject", "")
        message_body = body.get("message_body", "")
        cc = body.get("cc")
        bcc = body.get("bcc")
        doc_ref = body.get("document_ref")
        user_notes = body.get("user_notes")

        # Initial Status strictly compliant with rules:
        status = "WhatsApp opened" if channel == "whatsapp" else "Email draft opened"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO communications (
                    user_id, username, channel, party_id, party_name, contact_person,
                    recipient_contact, cc, bcc, deal_id, chain_id, message_type,
                    subject, message_body, document_ref, status, user_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, channel, party_id, party_name, contact_person,
                recipient, cc, bcc, deal_id, chain_id, message_type,
                subject, message_body, doc_ref, status, user_notes
            ))
            comm_id = cursor.lastrowid

            if party_id:
                if channel == "whatsapp":
                    conn.execute("UPDATE parties SET last_whatsapp_date = CURRENT_TIMESTAMP WHERE id = ?", (party_id,))
                else:
                    conn.execute("UPDATE parties SET last_email_date = CURRENT_TIMESTAMP WHERE id = ?", (party_id,))

            log_audit(
                user_id=user_id, username=username, action="COMMUNICATION",
                entity_type="communication", entity_id=str(comm_id),
                notes=f"Opened {channel.upper()} draft to {party_name} ({recipient}) for {message_type}",
                conn=conn
            )

            self._send_json({
                "success": True,
                "communication_id": comm_id,
                "status": status,
                "message": f"{channel.title()} communication logged successfully."
            })

    def _get_communications(self, query: Dict[str, List[str]]):
        """Retrieves communication history log with multi-field filtering."""
        with get_db() as conn:
            sql = """
                SELECT c.*, u.full_name as initiator_name
                FROM communications c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE COALESCE(c.is_deleted, 0) = 0
            """
            params = []

            if "party_id" in query and query["party_id"][0]:
                sql += " AND c.party_id = ?"
                params.append(int(query["party_id"][0]))

            if "deal_id" in query and query["deal_id"][0]:
                sql += " AND c.deal_id = ?"
                params.append(int(query["deal_id"][0]))

            if "chain_id" in query and query["chain_id"][0]:
                sql += " AND c.chain_id = ?"
                params.append(int(query["chain_id"][0]))

            if "channel" in query and query["channel"][0]:
                sql += " AND c.channel = ?"
                params.append(query["channel"][0])

            if "status" in query and query["status"][0]:
                sql += " AND c.status = ?"
                params.append(query["status"][0])

            sql += " ORDER BY c.id DESC LIMIT 100"

            rows = conn.execute(sql, params).fetchall()
            self._send_json({"success": True, "communications": rows_to_dict_list(rows)})

    def _update_communication_status(self, comm_id: int, body: Dict[str, Any], user_id: int, username: str):
        """Updates communication status (e.g. 'Manually marked as sent', 'Client confirmed')."""
        new_status = body.get("status")
        valid_statuses = (
            "WhatsApp opened",
            "Email draft opened",
            "Manually marked as sent",
            "Client confirmed",
            "Client requested amendment",
            "Failed to open",
            "Cancelled before opening"
        )
        if new_status not in valid_statuses:
            self._send_error(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            return

        user_notes = body.get("user_notes")

        with get_db() as conn:
            comm = row_to_dict(conn.execute("SELECT * FROM communications WHERE id = ?", (comm_id,)).fetchone())
            if not comm:
                self._send_error("Communication record not found", 404)
                return

            conn.execute("""
                UPDATE communications SET
                    status = ?,
                    user_notes = COALESCE(?, user_notes)
                WHERE id = ?
            """, (new_status, user_notes, comm_id))

            log_audit(
                user_id=user_id, username=username, action="COMM_STATUS",
                entity_type="communication", entity_id=str(comm_id),
                notes=f"Updated communication #{comm_id} status to '{new_status}'",
                conn=conn
            )

            self._send_json({"success": True, "message": f"Status updated to '{new_status}'."})


def run_server(port: int = PORT):
    seed_database()
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, GncApiHandler)
    print(f"================================================================")
    print(f" G&C Central Deal and Brokerage Automation Platform Running")
    print(f" Access URL: http://localhost:{port}")
    print(f" Database: {DB_PATH}")
    print(f" Static Dir: {STATIC_DIR}")
    print(f"================================================================")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
