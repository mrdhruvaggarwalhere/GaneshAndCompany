"""
G&C Central Deal and Brokerage Automation Platform
Seed Data & Mandatory Worked Example Acceptance Scenario
"""
from decimal import Decimal
from database import get_db, init_db, row_to_dict
from auth_audit import hash_password, log_audit
from calculations import compute_deal_summary, compute_chain_totals, to_decimal
from models import normalize_name


def seed_database():
    """Initializes tables and seeds master data, users, and the mandatory worked scenario."""
    init_db()

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if users already exist
        existing_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing_users == 0:
            users_data = [
                ("admin", hash_password("admin123"), "Administrator", "admin", "admin@ganeshandco.com"),
                ("broker", hash_password("broker123"), "Senior Oil Broker", "broker", "broker@ganeshandco.com"),
                ("accounts", hash_password("accounts123"), "Accounts Head", "accounts", "accounts@ganeshandco.com"),
                ("viewer", hash_password("viewer123"), "Management Viewer", "viewer", "viewer@ganeshandco.com"),
            ]
            cursor.executemany("""
                INSERT INTO users (username, password_hash, full_name, role, email)
                VALUES (?, ?, ?, ?, ?)
            """, users_data)

        # Master Parties
        existing_parties = cursor.execute("SELECT COUNT(*) FROM parties").fetchone()[0]
        parties_data = [
            ("HARYANA INDUSTRIES, PANCHKULA", "both", "Panchkula", "Haryana", "06AAACH1111A1Z5", 50.0, 50.0, "BUSY_HAR_01", "Shri R.K. Aggarwal", "919812000001", "trading@haryanaindustries.com", "919812000011", "accounts@haryanaindustries.com"),
            ("NAGPAL ENTERPRISES PVT. LTD., ANOUPGARH", "seller", "Anoupgarh", "Rajasthan", "08AAACN2222B1Z6", 50.0, 50.0, "BUSY_NAG_01", "Shri Suresh Nagpal", "919812000002", "sales@nagpalenterprises.com", "919812000012", "info@nagpalenterprises.com"),
            ("M.L. NAGPAL INDUSTRIES, ANOUPGARH", "both", "Anoupgarh", "Rajasthan", "08AAACM3333C1Z7", 50.0, 50.0, "BUSY_MLN_01", "Shri M.L. Nagpal", "919812000003", "mlnagpal@mlnindustries.com", "919812000013", "accounts@mlnindustries.com"),
            ("SHAKTI NUTRITIONS PVT. LTD.", "buyer", "Ludhiana", "Punjab", "03AAACS4444D1Z8", 50.0, 50.0, "BUSY_SHK_01", "Shri Ramesh Shakti", "919812000004", "procurement@shaktinutritions.com", "919812000014", "finance@shaktinutritions.com"),
            ("SHREE RAM OIL MILLS, JAIPUR", "both", "Jaipur", "Rajasthan", "08AAACS5555E1Z9", 40.0, 40.0, "BUSY_SRO_01", "Shri Gopal Sharma", "919812000005", "info@shreeramoils.com", "919812000015", "accounts@shreeramoils.com"),
            ("MAHALAXMI AGRO OILS, KANPUR", "both", "Kanpur", "Uttar Pradesh", "09AAACM6666F1Z0", 45.0, 45.0, "BUSY_MAO_01", "Shri Anand Gupta", "919812000006", "trade@mahalaxmioils.com", "919812000016", "billing@mahalaxmioils.com"),
            ("ADANI WILMAR LIMITED, GUJARAT", "both", "Ahmedabad", "Gujarat", "24AAACA7777G1Z1", 60.0, 60.0, "BUSY_AWL_01", "Shri Sanjay Mehta", "919812000007", "commodity@adaniwilmar.in", "919812000017", "accounts@adaniwilmar.in"),
        ]

        if existing_parties == 0:
            for p in parties_data:
                cursor.execute("""
                    INSERT INTO parties (
                        name, normalized_name, party_type, city, state, gstin,
                        default_buyer_brokerage_rate, default_seller_brokerage_rate, busy_ledger_id,
                        contact_person, phone, email, whatsapp_primary, whatsapp_secondary,
                        email_primary, email_secondary, preferred_comm_method, preferred_language
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'both', 'english')
                """, (p[0], normalize_name(p[0]), p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[9], p[11], p[10], p[12]))
        else:
            # Enrich existing parties if contact fields are empty
            for p in parties_data:
                cursor.execute("""
                    UPDATE parties SET
                        contact_person = COALESCE(contact_person, ?),
                        phone = COALESCE(phone, ?),
                        email = COALESCE(email, ?),
                        whatsapp_primary = COALESCE(whatsapp_primary, ?),
                        whatsapp_secondary = COALESCE(whatsapp_secondary, ?),
                        email_primary = COALESCE(email_primary, ?),
                        email_secondary = COALESCE(email_secondary, ?),
                        preferred_comm_method = COALESCE(preferred_comm_method, 'both'),
                        preferred_language = COALESCE(preferred_language, 'english')
                    WHERE name LIKE ?
                """, (p[8], p[9], p[10], p[9], p[11], p[10], p[12], f"{p[0][:15]}%"))

        # Master Products
        existing_products = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if existing_products == 0:
            products_data = [
                ("MUSTARD OIL", "M.OIL", "quintals", 5.0, "1514", "BUSY_ITM_MOIL"),
                ("REFINED SOYBEAN OIL", "SOYA.OIL", "quintals", 5.0, "1507", "BUSY_ITM_SOYA"),
                ("RBD PALM OIL", "PALM.OIL", "quintals", 5.0, "1511", "BUSY_ITM_PALM"),
                ("SUNFLOWER OIL", "SUN.OIL", "quintals", 5.0, "1512", "BUSY_ITM_SUN"),
                ("MUSTARD SEED", "M.SEED", "quintals", 5.0, "1205", "BUSY_ITM_MSEED"),
            ]
            for prod in products_data:
                cursor.execute("""
                    INSERT INTO products (name, code, default_unit, default_gst_pct, hsn_sac, busy_item_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, prod)

        # Settings
        default_settings = [
            ("company_name", "Ganesh & Company", "Company legal/trade name"),
            ("company_tagline", "Central Edible Oil Brokerage & Commodity Trading", "Tagline"),
            ("gst_on_brokerage", "false", "Whether GST applies to brokerage earnings"),
            ("gst_brokerage_rate", "18.0", "GST percentage on brokerage when enabled"),
            ("default_brokerage_rate_per_tonne", "50.0", "Default per-tonne brokerage in ₹"),
            ("busy_export_enabled", "true", "Enable intermediate BUSY export staging"),
        ]
        for k, v, desc in default_settings:
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            """, (k, v, desc))

        # Check if Worked Example Acceptance Chain exists, if not seed it
        existing_chains = cursor.execute("SELECT COUNT(*) FROM deal_chains").fetchone()[0]
        if existing_chains == 0:
            seed_worked_acceptance_scenario(cursor)


def seed_worked_acceptance_scenario(cursor):
    """
    Seeds the mandatory acceptance scenario:
    - Deal 1 (01/07/2026): HARYANA INDUSTRIES buys 320 quintals M.OIL from NAGPAL ENTERPRISES @ ₹15,700 + GST. Delivery 31/07/2026.
    - Deal 2 (18/07/2026): HARYANA authorizes @ ₹16,450. Sold to M.L. NAGPAL @ ₹16,475 + GST. Profit = ₹8,000.
    - Deal 3 (30/07/2026): M.L. NAGPAL authorizes @ ₹16,475. Sold to SHAKTI NUTRITIONS on 11/08/2026 @ ₹16,700 + GST. Profit = ₹72,000.
    - Result: Total Price Diff Profit = ₹80,000. Direct Billing: NAGPAL ENTERPRISES -> SHAKTI NUTRITIONS (or HARYANA -> SHAKTI).
    """
    p_nagpal = cursor.execute("SELECT id FROM parties WHERE name LIKE 'NAGPAL ENTERPRISES%'").fetchone()[0]
    p_haryan = cursor.execute("SELECT id FROM parties WHERE name LIKE 'HARYANA INDUSTRIES%'").fetchone()[0]
    p_mlnag = cursor.execute("SELECT id FROM parties WHERE name LIKE 'M.L. NAGPAL%'").fetchone()[0]
    p_shakti = cursor.execute("SELECT id FROM parties WHERE name LIKE 'SHAKTI NUTRITIONS%'").fetchone()[0]
    prod_moil = cursor.execute("SELECT id FROM products WHERE code = 'M.OIL'").fetchone()[0]
    u_admin = cursor.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]

    # Create Chain
    cursor.execute("""
        INSERT INTO deal_chains (
            chain_code, product_id, initial_quantity_qtl, remaining_quantity_qtl,
            original_bill_seller_id, final_bill_buyer_id, final_billing_rate, status, notes, created_by_user_id
        ) VALUES ('CHN-2026-0001', ?, 320.0, 320.0, ?, ?, 16700.0, 'ready_for_billing', 'Mandatory worked acceptance test lot (320 Qtl / 32 MT)', ?)
    """, (prod_moil, p_haryan, p_shakti, u_admin))
    chain_id = cursor.lastrowid

    # Deal 1: Initial Purchase (01/07/2026)
    d1_summary = compute_deal_summary({
        "quantity_qtl": 320.0,
        "rate_per_qtl": 15700.0,
        "gst_applicable": True,
        "gst_pct": 5.0,
        "buyer_brokerage_rate_per_tonne": 50.0,
        "seller_brokerage_rate_per_tonne": 50.0
    })

    cursor.execute("""
        INSERT INTO deals (
            deal_number, chain_id, parent_deal_id, deal_date, instruction_date,
            buyer_id, seller_id, product_id, quantity_qtl, quantity_tonnes,
            rate_per_qtl, gst_applicable, gst_pct, taxable_value, gst_amount, total_value,
            authorized_rate_per_qtl, actual_rate_per_qtl, price_diff_per_qtl, price_diff_profit,
            buyer_brokerage_rate_per_tonne, buyer_brokerage_amount,
            seller_brokerage_rate_per_tonne, seller_brokerage_amount,
            total_brokerage, total_deal_earning, delivery_date, status, created_by_user_id
        ) VALUES (
            'DL-2026-0001', ?, NULL, '2026-07-01', '2026-07-01',
            ?, ?, ?, 320.0, 32.0,
            15700.0, 1, 5.0, ?, ?, ?,
            0.0, 15700.0, 0.0, 0.0,
            50.0, ?, 50.0, ?,
            ?, ?, '2026-07-31', 'completed', ?
        )
    """, (
        chain_id, p_haryan, p_nagpal, prod_moil,
        float(d1_summary["taxable_value"]), float(d1_summary["gst_amount"]), float(d1_summary["total_value"]),
        float(d1_summary["buyer_brokerage_amount"]), float(d1_summary["seller_brokerage_amount"]),
        float(d1_summary["total_brokerage"]), float(d1_summary["total_deal_earning"]), u_admin
    ))
    deal1_id = cursor.lastrowid

    # Deal 2: First Resale Link (18/07/2026)
    # HARYANA instructs @ 16,450; Sold to M.L. NAGPAL @ 16,475. Diff = +25. Profit = 25 * 320 = 8,000
    d2_summary = compute_deal_summary({
        "quantity_qtl": 320.0,
        "rate_per_qtl": 16475.0,
        "authorized_rate_per_qtl": 16450.0,
        "actual_rate_per_qtl": 16475.0,
        "gst_applicable": True,
        "gst_pct": 5.0,
        "buyer_brokerage_rate_per_tonne": 50.0,
        "seller_brokerage_rate_per_tonne": 50.0
    })

    cursor.execute("""
        INSERT INTO deals (
            deal_number, chain_id, parent_deal_id, deal_date, instruction_date,
            buyer_id, seller_id, product_id, quantity_qtl, quantity_tonnes,
            rate_per_qtl, gst_applicable, gst_pct, taxable_value, gst_amount, total_value,
            authorized_rate_per_qtl, actual_rate_per_qtl, price_diff_per_qtl, price_diff_profit,
            buyer_brokerage_rate_per_tonne, buyer_brokerage_amount,
            seller_brokerage_rate_per_tonne, seller_brokerage_amount,
            total_brokerage, total_deal_earning, delivery_date, status, created_by_user_id
        ) VALUES (
            'DL-2026-0002', ?, ?, '2026-07-18', '2026-07-18',
            ?, ?, ?, 320.0, 32.0,
            16475.0, 1, 5.0, ?, ?, ?,
            16450.0, 16475.0, 25.0, 8000.0,
            50.0, ?, 50.0, ?,
            ?, ?, '2026-07-31', 'completed', ?
        )
    """, (
        chain_id, deal1_id, p_mlnag, p_haryan, prod_moil,
        float(d2_summary["taxable_value"]), float(d2_summary["gst_amount"]), float(d2_summary["total_value"]),
        float(d2_summary["buyer_brokerage_amount"]), float(d2_summary["seller_brokerage_amount"]),
        float(d2_summary["total_brokerage"]), float(d2_summary["total_deal_earning"]), u_admin
    ))
    deal2_id = cursor.lastrowid

    # Deal 3: Second Resale Link (30/07/2026 / 11/08/2026)
    # M.L. NAGPAL instructs @ 16,475; Sold to SHAKTI NUTRITIONS @ 16,700. Diff = +225. Profit = 225 * 320 = 72,000
    d3_summary = compute_deal_summary({
        "quantity_qtl": 320.0,
        "rate_per_qtl": 16700.0,
        "authorized_rate_per_qtl": 16475.0,
        "actual_rate_per_qtl": 16700.0,
        "gst_applicable": True,
        "gst_pct": 5.0,
        "buyer_brokerage_rate_per_tonne": 50.0,
        "seller_brokerage_rate_per_tonne": 50.0
    })

    cursor.execute("""
        INSERT INTO deals (
            deal_number, chain_id, parent_deal_id, deal_date, instruction_date,
            buyer_id, seller_id, product_id, quantity_qtl, quantity_tonnes,
            rate_per_qtl, gst_applicable, gst_pct, taxable_value, gst_amount, total_value,
            authorized_rate_per_qtl, actual_rate_per_qtl, price_diff_per_qtl, price_diff_profit,
            buyer_brokerage_rate_per_tonne, buyer_brokerage_amount,
            seller_brokerage_rate_per_tonne, seller_brokerage_amount,
            total_brokerage, total_deal_earning, delivery_date, status, created_by_user_id
        ) VALUES (
            'DL-2026-0003', ?, ?, '2026-07-30', '2026-07-30',
            ?, ?, ?, 320.0, 32.0,
            16700.0, 1, 5.0, ?, ?, ?,
            16475.0, 16700.0, 225.0, 72000.0,
            50.0, ?, 50.0, ?,
            ?, ?, '2026-08-11', 'confirmed', ?
        )
    """, (
        chain_id, deal2_id, p_shakti, p_mlnag, prod_moil,
        float(d3_summary["taxable_value"]), float(d3_summary["gst_amount"]), float(d3_summary["total_value"]),
        float(d3_summary["buyer_brokerage_amount"]), float(d3_summary["seller_brokerage_amount"]),
        float(d3_summary["total_brokerage"]), float(d3_summary["total_deal_earning"]), u_admin
    ))


if __name__ == "__main__":
    seed_database()
    print("Database schema and seed data initialized successfully.")
