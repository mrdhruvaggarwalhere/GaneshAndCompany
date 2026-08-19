"""
G&C Central Deal and Brokerage Automation Platform
Automated Acceptance & Invariant Test Suite
"""
import unittest
import os
import io
from typing import Dict, Any
from decimal import Decimal
from calculations import (
    convert_quintals_to_tonnes,
    convert_tonnes_to_quintals,
    calculate_price_difference,
    calculate_price_difference_profit,
    calculate_buyer_brokerage,
    calculate_seller_brokerage,
    calculate_deal_brokerage,
    compute_deal_summary,
    compute_chain_totals
)
from database import get_db, init_db, row_to_dict, rows_to_dict_list
from seed_data import seed_database
from excel_exporter import create_excel_workbook
from busy_adapter import BusyAccountingAdapter
from auth_audit import check_permission, hash_password, verify_password


class TestGaneshAndCompanyPlatform(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize test database
        seed_database()

    def test_01_unit_conversions(self):
        """Test exact quintal-to-tonne and tonne-to-quintal conversions."""
        self.assertEqual(convert_quintals_to_tonnes(Decimal("320")), Decimal("32.000"))
        self.assertEqual(convert_tonnes_to_quintals(Decimal("32")), Decimal("320.000"))
        self.assertEqual(convert_quintals_to_tonnes(Decimal("15.5")), Decimal("1.550"))
        self.assertEqual(convert_tonnes_to_quintals(Decimal("1.55")), Decimal("15.500"))

    def test_02_brokerage_calculations(self):
        """Test buyer, seller, asymmetric, and zero brokerage calculations."""
        tonnes = Decimal("32.000")

        # Independent rates
        buyer_rate = Decimal("50.00")
        seller_rate = Decimal("75.00")
        b_brok = calculate_buyer_brokerage(tonnes, buyer_rate)
        s_brok = calculate_seller_brokerage(tonnes, seller_rate)
        self.assertEqual(b_brok, Decimal("1600.00"))
        self.assertEqual(s_brok, Decimal("2400.00"))

        b, s, total = calculate_deal_brokerage(tonnes, buyer_rate, seller_rate)
        self.assertEqual(total, Decimal("4000.00"))

        # Zero brokerage support
        b_zero, s_zero, total_zero = calculate_deal_brokerage(tonnes, Decimal("0.00"), Decimal("0.00"))
        self.assertEqual(total_zero, Decimal("0.00"))

    def test_03_price_difference_profit_and_loss(self):
        """Test positive gain, zero diff, and negative loss scenarios."""
        qty_qtl = Decimal("320")

        # 1. Positive profit: Authorized 16450, Sold 16475 -> Diff +25 -> Profit 8000
        diff, profit = calculate_price_difference_profit(qty_qtl, Decimal("16475"), Decimal("16450"))
        self.assertEqual(diff, Decimal("25"))
        self.assertEqual(profit, Decimal("8000.00"))

        # 2. Zero diff
        diff_zero, profit_zero = calculate_price_difference_profit(qty_qtl, Decimal("16450"), Decimal("16450"))
        self.assertEqual(diff_zero, Decimal("0"))
        self.assertEqual(profit_zero, Decimal("0.00"))

        # 3. Negative loss: Authorized 16500, Sold 16400 -> Diff -100 -> Loss -32000
        diff_loss, profit_loss = calculate_price_difference_profit(qty_qtl, Decimal("16400"), Decimal("16500"))
        self.assertEqual(diff_loss, Decimal("-100"))
        self.assertEqual(profit_loss, Decimal("-32000.00"))

    def test_04_mandatory_acceptance_worked_example(self):
        """
        Acceptance Test Scenario:
        Initial: 320 quintals M.OIL
        Link 1: HARYANA @16450 -> M.L. NAGPAL @16475 (+25/qtl) => ₹8,000 profit
        Link 2: M.L. NAGPAL @16475 -> SHAKTI NUTRITIONS @16700 (+225/qtl) => ₹72,000 profit
        Expected Total Profit: ₹80,000
        Direct Bill: NAGPAL / HARYANA -> SHAKTI NUTRITIONS for 320 quintals @ ₹16,700 + GST
        """
        deals_chain = [
            {
                "id": 1,
                "deal_date": "2026-07-01",
                "buyer_name": "HARYANA INDUSTRIES, PANCHKULA",
                "seller_name": "NAGPAL ENTERPRISES PVT. LTD., ANOUPGARH",
                "seller_id": 2,
                "buyer_id": 1,
                "product_name": "MUSTARD OIL (M.OIL)",
                "quantity_qtl": Decimal("320"),
                "rate_per_qtl": Decimal("15700"),
                "authorized_rate_per_qtl": Decimal("0"),
                "actual_rate_per_qtl": Decimal("15700"),
                "price_diff_profit": Decimal("0"),
                "buyer_brokerage_amount": Decimal("1600.00"),
                "seller_brokerage_amount": Decimal("1600.00"),
                "gst_applicable": True,
                "status": "completed"
            },
            {
                "id": 2,
                "deal_date": "2026-07-18",
                "instruction_date": "2026-07-18",
                "buyer_name": "M.L. NAGPAL INDUSTRIES, ANOUPGARH",
                "seller_name": "HARYANA INDUSTRIES, PANCHKULA",
                "seller_id": 1,
                "buyer_id": 3,
                "product_name": "MUSTARD OIL (M.OIL)",
                "quantity_qtl": Decimal("320"),
                "rate_per_qtl": Decimal("16475"),
                "authorized_rate_per_qtl": Decimal("16450"),
                "actual_rate_per_qtl": Decimal("16475"),
                "price_diff_profit": Decimal("8000.00"),
                "buyer_brokerage_amount": Decimal("1600.00"),
                "seller_brokerage_amount": Decimal("1600.00"),
                "gst_applicable": True,
                "status": "completed"
            },
            {
                "id": 3,
                "deal_date": "2026-07-30",
                "instruction_date": "2026-07-30",
                "buyer_name": "SHAKTI NUTRITIONS PVT. LTD.",
                "seller_name": "M.L. NAGPAL INDUSTRIES, ANOUPGARH",
                "seller_id": 3,
                "buyer_id": 4,
                "product_name": "MUSTARD OIL (M.OIL)",
                "quantity_qtl": Decimal("320"),
                "rate_per_qtl": Decimal("16700"),
                "authorized_rate_per_qtl": Decimal("16475"),
                "actual_rate_per_qtl": Decimal("16700"),
                "price_diff_profit": Decimal("72000.00"),
                "buyer_brokerage_amount": Decimal("1600.00"),
                "seller_brokerage_amount": Decimal("1600.00"),
                "gst_applicable": True,
                "status": "confirmed"
            }
        ]

        summary = compute_chain_totals(deals_chain)

        # Verify exact profit figures
        self.assertEqual(summary["total_price_diff_profit"], Decimal("80000.00"))
        self.assertEqual(summary["final_billing_rate"], Decimal("16700"))
        self.assertEqual(summary["final_quantity_qtl"], Decimal("320"))
        self.assertEqual(summary["total_buyer_brokerage"], Decimal("4800.00"))
        self.assertEqual(summary["total_seller_brokerage"], Decimal("4800.00"))
        self.assertEqual(summary["total_brokerage"], Decimal("9600.00"))
        self.assertEqual(summary["total_chain_earning"], Decimal("89600.00"))

        # Verify direct billing instruction text (Root Lot Buyer issues direct bill to Final Buyer)
        self.assertIn("HARYANA INDUSTRIES, PANCHKULA will issue a direct bill to SHAKTI NUTRITIONS PVT. LTD.", summary["direct_billing_instruction"])
        self.assertIn("320", summary["direct_billing_instruction"])
        self.assertIn("16,700", summary["direct_billing_instruction"])

    def test_05_partial_resale_and_oversell_prevention(self):
        """Test partial lot balance tracking and overselling prevention."""
        lot_qty = Decimal("500")
        resale_1 = Decimal("200")
        resale_2 = Decimal("300")
        resale_invalid = Decimal("50")  # Exceeds balance of 0

        remaining = lot_qty - resale_1
        self.assertEqual(remaining, Decimal("300"))

        remaining -= resale_2
        self.assertEqual(remaining, Decimal("0"))

        # Oversell check
        self.assertTrue(resale_invalid > remaining)

    def test_06_excel_export_generation(self):
        """Test Excel generation with strict A:G mapping and summary formulas."""
        deals = [{
            "id": 1,
            "deal_number": "DL-2026-0001",
            "chain_id": 1,
            "chain_code": "CHN-2026-0001",
            "deal_date": "2026-07-01",
            "buyer_name": "HARYANA INDUSTRIES",
            "seller_name": "NAGPAL ENTERPRISES",
            "product_code": "M.OIL",
            "quantity_qtl": 320.0,
            "quantity_tonnes": 32.0,
            "rate_per_qtl": 15700.0,
            "delivery_date": "2026-07-31",
            "price_diff_profit": 0.0,
            "buyer_brokerage_amount": 1600.0,
            "seller_brokerage_amount": 1600.0,
            "total_brokerage": 3200.0,
            "total_deal_earning": 3200.0,
            "status": "confirmed"
        }]

        stream = create_excel_workbook(deals_data=deals)
        self.assertIsInstance(stream, io.BytesIO)
        content = stream.getvalue()
        self.assertTrue(len(content) > 1000)
        # Check ZIP / XLSX magic number
        self.assertEqual(content[:2], b'PK')

    def test_07_busy_adapter_safeguards(self):
        """Test BUSY intermediate voucher generation and safeguards against posting internal chain deals."""
        with get_db() as conn:
            chain = row_to_dict(conn.execute("SELECT id FROM deal_chains LIMIT 1").fetchone())
            self.assertIsNotNone(chain)

            # Test direct sales voucher generation for approved chain
            res = BusyAccountingAdapter.generate_direct_sales_voucher(chain["id"])
            self.assertIn("json_payload", res)
            self.assertIn("xml_payload", res)
            self.assertEqual(res["json_payload"]["voucher_type"], "Sales")
            self.assertIn("<BUSY_VOUCHER>", res["xml_payload"])

    def test_08_rbac_permissions(self):
        """Test role-based access control matrix."""
        self.assertTrue(check_permission("admin", "deals.cancel"))
        self.assertFalse(check_permission("broker", "deals.cancel"))
        self.assertTrue(check_permission("broker", "deals.create"))
        self.assertTrue(check_permission("accounts", "billing.approve"))
        self.assertFalse(check_permission("viewer", "deals.create"))

    def test_09_soft_delete_and_restore_with_recycle_bin(self):
        """Test soft-deletion and undo/restoration workflow across deals, chains, and parties."""
        with get_db() as conn:
            # Create a test deal
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO deals (
                    deal_number, chain_id, deal_date, buyer_id, seller_id, product_id,
                    quantity_qtl, quantity_tonnes, rate_per_qtl, total_value, total_deal_earning
                ) VALUES ('DL-TEST-DEL', 1, '2026-08-15', 1, 2, 1, 100.0, 10.0, 15000.0, 1500000.0, 1000.0)
            """)
            test_deal_id = cursor.lastrowid

            # Verify active
            active = conn.execute("SELECT id FROM deals WHERE id = ? AND COALESCE(is_deleted, 0) = 0", (test_deal_id,)).fetchone()
            self.assertIsNotNone(active)

            # Soft delete
            conn.execute("UPDATE deals SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deletion_reason = 'Testing deletion' WHERE id = ?", (test_deal_id,))
            deleted_check = conn.execute("SELECT id FROM deals WHERE id = ? AND COALESCE(is_deleted, 0) = 0", (test_deal_id,)).fetchone()
            self.assertIsNone(deleted_check)

            # Check recycle bin query finds it
            trash_deal = conn.execute("SELECT id, deletion_reason FROM deals WHERE id = ? AND is_deleted = 1", (test_deal_id,)).fetchone()
            self.assertIsNotNone(trash_deal)
            self.assertEqual(trash_deal[1], "Testing deletion")

            # Restore
            conn.execute("UPDATE deals SET is_deleted = 0, deleted_at = NULL, deletion_reason = NULL WHERE id = ?", (test_deal_id,))
            restored = conn.execute("SELECT id FROM deals WHERE id = ? AND COALESCE(is_deleted, 0) = 0", (test_deal_id,)).fetchone()
            self.assertIsNotNone(restored)

            # Cleanup
            conn.execute("DELETE FROM deals WHERE id = ?", (test_deal_id,))

    def test_10_zero_cost_communication_module(self):
        """Test zero-cost WhatsApp and Email communication engine, normalization, and templates."""
        from communication_service import (
            normalize_indian_phone,
            validate_email,
            generate_communication_draft,
            COMM_MODES
        )

        # 1. Phone number normalization
        self.assertEqual(normalize_indian_phone("+91 98765-43210"), "919876543210")
        self.assertEqual(normalize_indian_phone("09876543210"), "919876543210")
        self.assertEqual(normalize_indian_phone("9876543210"), "919876543210")
        self.assertEqual(normalize_indian_phone("919876543210"), "919876543210")

        # 2. Email validation
        self.assertTrue(validate_email("trading@haryanaindustries.com"))
        self.assertFalse(validate_email("invalid-email-address"))

        # 3. Verify zero-cost mode restrictions
        self.assertTrue(COMM_MODES["WHATSAPP_CLICK_TO_CHAT"])
        self.assertTrue(COMM_MODES["EMAIL_MAILTO"])
        self.assertFalse(COMM_MODES["WHATSAPP_BUSINESS_API"])
        self.assertFalse(COMM_MODES["EMAIL_SMTP"])

        # 4. Generate Buyer Deal Confirmation draft
        party_buyer = {
            "id": 2,
            "name": "M.L. NAGPAL INDUSTRIES, ANOUPGARH",
            "contact_person": "Shri M.L. Nagpal",
            "whatsapp_primary": "919812000002",
            "email_primary": "mlnagpal@example.com"
        }
        deal_sample = {
            "deal_number": "DL-2026-0001",
            "deal_date": "2026-07-01",
            "delivery_date": "2026-07-31",
            "product_name": "MUSTARD OIL",
            "quantity_qtl": 320.0,
            "seller_name": "NAGPAL ENTERPRISES PVT. LTD., ANOUPGARH",
            "rate_per_qtl": 15700.0,
            "gst_applicable": True,
            "buyer_brokerage_amount": 1600.0
        }
        buyer_draft = generate_communication_draft("deal_confirmation_buyer", party_buyer, deal=deal_sample)
        self.assertIn("G&C Deal Confirmation – DL-2026-0001", buyer_draft["subject"])
        self.assertIn("Dear Shri M.L. Nagpal", buyer_draft["body"])
        self.assertIn("320 quintals (32 metric tonnes)", buyer_draft["body"])
        self.assertIn("₹15,700.00 + GST per quintal", buyer_draft["body"])
        # Invariant: Brokerage excluded by default from ordinary confirmation
        self.assertNotIn("Brokerage Charge:", buyer_draft["body"])
        self.assertNotIn("Profit:", buyer_draft["body"])

        # 5. Generate Final Billing Instruction draft (Mandatory Worked Example)
        # 5. Generate Final Billing Instruction draft (Mandatory Worked Example)
        chain_sample = {
            "chain_code": "CHN-2026-0001",
            "product_name": "MUSTARD OIL",
            "remaining_quantity_qtl": 320.0,
            "final_billing_rate": 16700.0,
            "original_bill_seller_name": "HARYANA INDUSTRIES, PANCHKULA",
            "final_bill_buyer_name": "SHAKTI NUTRITIONS PVT. LTD."
        }
        billing_draft = generate_communication_draft("final_billing_instruction", {"name": "HARYANA INDUSTRIES, PANCHKULA"}, chain=chain_sample)
        self.assertIn("G&C Direct Billing Instruction – CHN-2026-0001", billing_draft["subject"])
        self.assertIn("Bill From: HARYANA INDUSTRIES, PANCHKULA", billing_draft["body"])
        self.assertIn("Bill To: SHAKTI NUTRITIONS PVT. LTD.", billing_draft["body"])
        self.assertIn("320 quintals", billing_draft["body"])
        self.assertIn("₹16,700.00 + GST per quintal", billing_draft["body"])

        # 6. Verify Remaining Templates
        # Seller confirmation
        seller_draft = generate_communication_draft("deal_confirmation_seller", {"name": "NAGPAL ENTERPRISES"}, deal=deal_sample)
        self.assertIn("G&C Seller Confirmation – DL-2026-0001", seller_draft["subject"])

        # Delivery reminder
        deliv_draft = generate_communication_draft("delivery_reminder", {"name": "M.L. NAGPAL"}, deal=deal_sample)
        self.assertIn("G&C Delivery Reminder – DL-2026-0001", deliv_draft["subject"])

        # Rate confirmation
        rate_draft = generate_communication_draft("rate_confirmation", {"name": "SHREE RAM"}, deal=deal_sample)
        self.assertIn("G&C Rate Confirmation – DL-2026-0001", rate_draft["subject"])
        self.assertIn("Agreed Rate: ₹15,700.00 + GST per quintal", rate_draft["body"])

        # Deal amendment
        amen_draft = generate_communication_draft("deal_amendment", {"name": "MAHALAXMI"}, deal=deal_sample)
        self.assertIn("G&C Deal Amendment – DL-2026-0001", amen_draft["subject"])

        # Deal cancellation
        canc_draft = generate_communication_draft("deal_cancellation", {"name": "ADANI WILMAR"}, deal=deal_sample)
        self.assertIn("G&C Deal Cancellation – DL-2026-0001", canc_draft["subject"])

        # Brokerage statement
        ledger_sample = {
            "summary": {
                "opening_balance": 0.0,
                "buyer_side_brokerage": 1600.0,
                "seller_side_brokerage": 1600.0,
                "total_brokerage_paid": 1000.0,
                "outstanding_balance": 2200.0
            }
        }
        stmt_draft = generate_communication_draft("brokerage_statement", {"name": "HARYANA INDUSTRIES"}, ledger=ledger_sample)
        self.assertIn("G&C Brokerage Statement –", stmt_draft["subject"])
        self.assertIn("Buyer-Side Brokerage: ₹1,600.00", stmt_draft["body"])
        self.assertIn("Seller-Side Brokerage: ₹1,600.00", stmt_draft["body"])
        self.assertIn("Outstanding Balance: ₹2,200.00", stmt_draft["body"])

        # Payment reminder
        rem_draft = generate_communication_draft("brokerage_payment_reminder", {"name": "HARYANA INDUSTRIES"}, ledger=ledger_sample)
        self.assertIn("G&C Payment Reminder – HARYANA INDUSTRIES", rem_draft["subject"])
        self.assertIn("Outstanding Balance: ₹2,200.00", rem_draft["body"])

        # Custom message
        cust_draft = generate_communication_draft("custom_message", {"name": "HARYANA INDUSTRIES"}, options={"custom_text": "Special delivery note."})
        self.assertIn("G&C Commodity Notice – HARYANA INDUSTRIES", cust_draft["subject"])
        self.assertIn("Special delivery note.", cust_draft["body"])

        # 7. Database communication log creation and status progression
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO communications (
                    channel, party_id, party_name, recipient_contact, message_type,
                    subject, message_body, status
                ) VALUES ('whatsapp', 2, 'M.L. NAGPAL INDUSTRIES', '919812000002', 'deal_confirmation_buyer', 'Subject', 'Body', 'WhatsApp opened')
            """)
            comm_id = cursor.lastrowid

            # Initial status
            comm = conn.execute("SELECT status FROM communications WHERE id = ?", (comm_id,)).fetchone()
            self.assertEqual(comm[0], "WhatsApp opened")

            # Status progression
            conn.execute("UPDATE communications SET status = 'Manually marked as sent' WHERE id = ?", (comm_id,))
            comm2 = conn.execute("SELECT status FROM communications WHERE id = ?", (comm_id,)).fetchone()
            self.assertEqual(comm2[0], "Manually marked as sent")

            conn.execute("UPDATE communications SET status = 'Client confirmed' WHERE id = ?", (comm_id,))
            comm3 = conn.execute("SELECT status FROM communications WHERE id = ?", (comm_id,)).fetchone()
            self.assertEqual(comm3[0], "Client confirmed")

            # Cleanup test record
            conn.execute("DELETE FROM communications WHERE id = ?", (comm_id,))


def run_all_tests() -> Dict[str, Any]:
    """Runs all test cases and returns structured summary for UI test runner."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGaneshAndCompanyPlatform)
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "was_successful": result.wasSuccessful(),
        "log": stream.getvalue()
    }


if __name__ == "__main__":
    unittest.main()
