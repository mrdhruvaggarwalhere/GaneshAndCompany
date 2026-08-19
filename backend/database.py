"""
G&C Central Deal and Brokerage Automation Platform
Database Layer with SQLite, Foreign Keys, and Schema Migrations
"""
import sqlite3
import os
import json
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "gnc_brokerage.db"))


def get_connection() -> sqlite3.Connection:
    """Creates a connection to SQLite database with row factory and pragmas enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initializes normalized database schema with tables, indexes, and constraints."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'broker', 'accounts', 'viewer')),
            email TEXT,
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Parties table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            party_type TEXT NOT NULL CHECK(party_type IN ('buyer', 'seller', 'both')),
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            gstin TEXT,
            default_buyer_brokerage_rate REAL DEFAULT 0.0,
            default_seller_brokerage_rate REAL DEFAULT 0.0,
            brokerage_enabled INTEGER DEFAULT 1,
            credit_notes TEXT,
            busy_ledger_id TEXT,
            is_active INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            deleted_by_user_id INTEGER REFERENCES users(id),
            deletion_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # 3. Products table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            default_unit TEXT DEFAULT 'quintals',
            default_gst_pct REAL DEFAULT 5.0,
            hsn_sac TEXT DEFAULT '1514',
            busy_item_id TEXT,
            is_active INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            deleted_by_user_id INTEGER REFERENCES users(id),
            deletion_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4. Deal Chains (lots)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS deal_chains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chain_code TEXT UNIQUE NOT NULL,
            product_id INTEGER NOT NULL REFERENCES products(id),
            initial_quantity_qtl REAL NOT NULL,
            remaining_quantity_qtl REAL NOT NULL,
            original_bill_seller_id INTEGER REFERENCES parties(id),
            final_bill_buyer_id INTEGER REFERENCES parties(id),
            final_billing_rate REAL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'in_progress' CHECK(status IN ('in_progress', 'ready_for_billing', 'billed', 'cancelled')),
            notes TEXT,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            deleted_by_user_id INTEGER REFERENCES users(id),
            deletion_reason TEXT,
            created_by_user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 5. Deals table (intermediate & initial deals)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_number TEXT UNIQUE NOT NULL,
            chain_id INTEGER NOT NULL REFERENCES deal_chains(id) ON DELETE CASCADE,
            parent_deal_id INTEGER REFERENCES deals(id),
            deal_date TEXT NOT NULL,
            instruction_date TEXT,
            buyer_id INTEGER NOT NULL REFERENCES parties(id),
            seller_id INTEGER NOT NULL REFERENCES parties(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity_qtl REAL NOT NULL,
            quantity_tonnes REAL NOT NULL,
            rate_per_qtl REAL NOT NULL,
            gst_applicable INTEGER DEFAULT 1,
            gst_pct REAL DEFAULT 5.0,
            is_rate_gst_inclusive INTEGER DEFAULT 0,
            taxable_rate_per_qtl REAL DEFAULT 0.0,
            taxable_value REAL DEFAULT 0.0,
            gst_amount REAL DEFAULT 0.0,
            total_value REAL DEFAULT 0.0,
            authorized_rate_per_qtl REAL DEFAULT 0.0,
            actual_rate_per_qtl REAL DEFAULT 0.0,
            price_diff_per_qtl REAL DEFAULT 0.0,
            price_diff_profit REAL DEFAULT 0.0,
            buyer_brokerage_rate_per_tonne REAL DEFAULT 0.0,
            buyer_brokerage_amount REAL DEFAULT 0.0,
            seller_brokerage_rate_per_tonne REAL DEFAULT 0.0,
            seller_brokerage_amount REAL DEFAULT 0.0,
            total_brokerage REAL DEFAULT 0.0,
            total_deal_earning REAL DEFAULT 0.0,
            delivery_date TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('draft', 'confirmed', 'completed', 'cancelled', 'invoiced')),
            cancellation_reason TEXT,
            brokerage_override_reason TEXT,
            notes TEXT,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            deleted_by_user_id INTEGER REFERENCES users(id),
            deletion_reason TEXT,
            created_by_user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 6. Brokerage payments and adjustments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS brokerage_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL REFERENCES parties(id),
            deal_id INTEGER REFERENCES deals(id),
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_type TEXT NOT NULL CHECK(payment_type IN ('receipt', 'adjustment', 'discount', 'tds_deduction')),
            reference_number TEXT,
            bank_or_mode TEXT,
            notes TEXT,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP,
            deleted_by_user_id INTEGER REFERENCES users(id),
            deletion_reason TEXT,
            created_by_user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Run safe migrations for existing tables to ensure is_deleted columns exist
        _run_soft_delete_migrations(cursor)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parties_normalized_name ON parties(normalized_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parties_active ON parties(is_active);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parties_deleted ON parties(is_deleted);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chains_status ON deal_chains(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chains_deleted ON deal_chains(is_deleted);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_chain_id ON deals(chain_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_date ON deals(deal_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_buyer ON deals(buyer_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_seller ON deals(seller_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_deleted ON deals(is_deleted);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_party ON brokerage_payments(party_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_deleted ON brokerage_payments(is_deleted);")

        # 7. Immutable audit log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER REFERENCES users(id),
            username TEXT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            before_state TEXT,
            after_state TEXT,
            ip_address TEXT,
            notes TEXT
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);")

        # 8. BUSY Integration mappings & sync logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS busy_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL CHECK(entity_type IN ('party', 'product', 'tax', 'series')),
            local_id INTEGER NOT NULL,
            busy_id TEXT NOT NULL,
            busy_name TEXT,
            sync_status TEXT DEFAULT 'synced',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(entity_type, local_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS busy_sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_chain_id INTEGER REFERENCES deal_chains(id),
            voucher_type TEXT NOT NULL,
            voucher_payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'staged' CHECK(status IN ('staged', 'approved', 'posted', 'failed', 'rejected')),
            external_reference TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            approved_by_user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_at TIMESTAMP
        );
        """)

        # 9. Excel export log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS excel_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            export_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            version_number INTEGER DEFAULT 1,
            filters_applied TEXT,
            exported_by_user_id INTEGER REFERENCES users(id),
            exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 11. Communication log table (Zero-cost WhatsApp & Email)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS communications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            username TEXT,
            channel TEXT NOT NULL CHECK(channel IN ('whatsapp', 'email')),
            party_id INTEGER REFERENCES parties(id),
            party_name TEXT NOT NULL,
            contact_person TEXT,
            recipient_contact TEXT NOT NULL,
            cc TEXT,
            bcc TEXT,
            deal_id INTEGER REFERENCES deals(id),
            chain_id INTEGER REFERENCES deal_chains(id),
            message_type TEXT NOT NULL,
            subject TEXT,
            message_body TEXT NOT NULL,
            document_ref TEXT,
            status TEXT NOT NULL DEFAULT 'WhatsApp opened' CHECK(status IN (
                'WhatsApp opened',
                'Email draft opened',
                'Manually marked as sent',
                'Client confirmed',
                'Client requested amendment',
                'Failed to open',
                'Cancelled before opening'
            )),
            user_notes TEXT,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_party ON communications(party_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_deal ON communications(deal_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_chain ON communications(chain_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comm_status ON communications(status);")

        _run_soft_delete_migrations(cursor)


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Converts a SQLite Row into a dictionary."""
    if row is None:
        return None
    return dict(row)


def rows_to_dict_list(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Converts a list of SQLite Rows into a list of dictionaries."""
    return [dict(r) for r in rows]


def _run_soft_delete_migrations(cursor: sqlite3.Cursor):
    """Safely adds soft-delete and communication columns to existing SQLite tables if they are missing."""
    tables = {
        "parties": [
            "is_deleted INTEGER DEFAULT 0", "deleted_at TIMESTAMP", "deleted_by_user_id INTEGER", "deletion_reason TEXT",
            "whatsapp_primary TEXT", "whatsapp_secondary TEXT", "email_primary TEXT", "email_secondary TEXT",
            "preferred_comm_method TEXT DEFAULT 'both'", "preferred_language TEXT DEFAULT 'english'",
            "whatsapp_enabled INTEGER DEFAULT 1", "email_enabled INTEGER DEFAULT 1",
            "comm_consent_notes TEXT", "last_whatsapp_date TIMESTAMP", "last_email_date TIMESTAMP"
        ],
        "products": ["is_deleted INTEGER DEFAULT 0", "deleted_at TIMESTAMP", "deleted_by_user_id INTEGER", "deletion_reason TEXT"],
        "deal_chains": ["is_deleted INTEGER DEFAULT 0", "deleted_at TIMESTAMP", "deleted_by_user_id INTEGER", "deletion_reason TEXT"],
        "deals": ["is_deleted INTEGER DEFAULT 0", "deleted_at TIMESTAMP", "deleted_by_user_id INTEGER", "deletion_reason TEXT"],
        "brokerage_payments": ["is_deleted INTEGER DEFAULT 0", "deleted_at TIMESTAMP", "deleted_by_user_id INTEGER", "deletion_reason TEXT"],
    }

    for table_name, cols in tables.items():
        existing_cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()]
        for col_def in cols:
            col_name = col_def.split()[0]
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_def}")
                except sqlite3.OperationalError:
                    pass

    try:
        # Populate whatsapp_primary from phone and email_primary from email where empty
        cursor.execute("""
            UPDATE parties
            SET whatsapp_primary = CASE 
                WHEN phone IS NOT NULL AND phone != '' THEN 
                    CASE WHEN phone LIKE '91%' THEN phone ELSE '91' || replace(replace(replace(replace(phone, '+', ''), ' ', ''), '-', ''), '(', '') END
                ELSE whatsapp_primary
            END
            WHERE whatsapp_primary IS NULL OR whatsapp_primary = '';
        """)
        cursor.execute("""
            UPDATE parties
            SET email_primary = email
            WHERE (email_primary IS NULL OR email_primary = '') AND email IS NOT NULL AND email != '';
        """)
    except Exception:
        pass

    try:
        # Align all chains so original_bill_seller_id is the buyer_id of the Root Lot Purchase (Link #1)
        cursor.execute("""
            UPDATE deal_chains
            SET original_bill_seller_id = (
                SELECT buyer_id FROM deals WHERE chain_id = deal_chains.id ORDER BY id ASC LIMIT 1
            )
            WHERE EXISTS (SELECT 1 FROM deals WHERE chain_id = deal_chains.id)
        """)
    except Exception:
        pass
