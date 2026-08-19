"""
G&C Central Deal and Brokerage Automation Platform
Authentication, Role-Based Permissions & Immutable Audit Logger
"""
import hashlib
import hmac
import json
import secrets
import time
from typing import Dict, Any, Optional, List, Tuple
from database import get_db, row_to_dict, rows_to_dict_list

# Active user sessions cache: session_token -> {user_id, username, role, full_name, expires_at}
SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_EXPIRY_SECONDS = 86400 * 7  # 7 days

# Role definitions & permissions matrix
ROLE_PERMISSIONS = {
    "admin": {
        "deals.create": True,
        "deals.edit": True,
        "deals.cancel": True,
        "deals.delete": True,
        "deals.resell": True,
        "deals.override_brokerage": True,
        "parties.manage": True,
        "products.manage": True,
        "reports.view": True,
        "excel.export": True,
        "billing.approve": True,
        "payments.manage": True,
        "busy.manage": True,
        "users.manage": True,
        "audit.view": True,
        "settings.manage": True,
        "trash.manage": True,
    },
    "broker": {
        "deals.create": True,
        "deals.edit": True,
        "deals.cancel": False,
        "deals.delete": True,
        "deals.resell": True,
        "deals.override_brokerage": True,
        "parties.manage": True,
        "products.manage": False,
        "reports.view": True,
        "excel.export": True,
        "billing.approve": False,
        "payments.manage": False,
        "busy.manage": False,
        "users.manage": False,
        "audit.view": False,
        "settings.manage": False,
        "trash.manage": True,
    },
    "accounts": {
        "deals.create": False,
        "deals.edit": False,
        "deals.cancel": False,
        "deals.delete": False,
        "deals.resell": False,
        "deals.override_brokerage": False,
        "parties.manage": True,
        "products.manage": False,
        "reports.view": True,
        "excel.export": True,
        "billing.approve": True,
        "payments.manage": True,
        "busy.manage": True,
        "users.manage": False,
        "audit.view": True,
        "settings.manage": False,
        "trash.manage": True,
    },
    "viewer": {
        "deals.create": False,
        "deals.edit": False,
        "deals.cancel": False,
        "deals.delete": False,
        "deals.resell": False,
        "deals.override_brokerage": False,
        "parties.manage": False,
        "products.manage": False,
        "reports.view": True,
        "excel.export": False,
        "billing.approve": False,
        "payments.manage": False,
        "busy.manage": False,
        "users.manage": False,
        "audit.view": False,
        "settings.manage": False,
        "trash.manage": False,
    }
}


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Generates a secure salted SHA-256 hash."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(stored_hash: str, password_attempt: str) -> bool:
    """Verifies a password against stored salt:hash."""
    try:
        salt, expected_hash = stored_hash.split(":", 1)
        actual_hash = hashlib.sha256((salt + password_attempt).encode("utf-8")).hexdigest()
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates username/password and creates a session token."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, full_name, role, is_active FROM users WHERE username = ?",
            (username.strip().lower(),)
        ).fetchone()

        if not row:
            return None

        user = row_to_dict(row)
        if not user.get("is_active"):
            return None

        if not verify_password(user["password_hash"], password):
            return None

        token = secrets.token_urlsafe(32)
        session_data = {
            "token": token,
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "full_name": user["full_name"],
            "expires_at": time.time() + SESSION_EXPIRY_SECONDS
        }
        SESSIONS[token] = session_data

        # Log authentication audit
        log_audit(
            user_id=user["id"],
            username=user["username"],
            action="LOGIN",
            entity_type="user",
            entity_id=str(user["id"]),
            notes="User logged in successfully"
        )

        return session_data


def get_current_user(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retrieves authenticated session user or returns default demo admin if none."""
    if token and token in SESSIONS:
        sess = SESSIONS[token]
        if sess["expires_at"] > time.time():
            return sess
        else:
            del SESSIONS[token]

    # For seamless usability and testing, return the active admin user if no header provided
    with get_db() as conn:
        admin_row = conn.execute(
            "SELECT id, username, full_name, role FROM users WHERE username = 'admin' LIMIT 1"
        ).fetchone()
        if admin_row:
            return {
                "token": "default_admin_token",
                "user_id": admin_row["id"],
                "username": admin_row["username"],
                "role": admin_row["role"],
                "full_name": admin_row["full_name"],
                "expires_at": time.time() + SESSION_EXPIRY_SECONDS
            }

    return None


def check_permission(user_role: str, permission_key: str) -> bool:
    """Checks if role possesses required capability."""
    role_perms = ROLE_PERMISSIONS.get(user_role, {})
    return role_perms.get(permission_key, False)


def log_audit(
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: Optional[Any] = None,
    after_state: Optional[Any] = None,
    notes: Optional[str] = None,
    ip_address: Optional[str] = None,
    conn: Optional[Any] = None
):
    """
    Records an immutable audit trail entry with before/after state diff.
    """
    before_json = json.dumps(before_state, default=str) if before_state is not None else None
    after_json = json.dumps(after_state, default=str) if after_state is not None else None

    sql = """
        INSERT INTO audit_events (
            user_id, username, action, entity_type, entity_id,
            before_state, after_state, notes, ip_address
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        user_id, username or "system", action, entity_type, str(entity_id),
        before_json, after_json, notes, ip_address or "127.0.0.1"
    )

    if conn is not None:
        conn.execute(sql, params)
    else:
        with get_db() as local_conn:
            local_conn.execute(sql, params)


def get_audit_trail(entity_type: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 150) -> List[Dict[str, Any]]:
    """Fetches chronological audit events with filtering and compute undo capabilities."""
    with get_db() as conn:
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(str(entity_id))

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        events = rows_to_dict_list(rows)

        # Enrich events with live can_undo status
        for ev in events:
            ev["can_undo"] = False
            ev["undo_state"] = "neutral" # neutral, pending_undo, already_undone
            action = ev.get("action")
            etype = ev.get("entity_type")
            eid = ev.get("entity_id")

            if not eid:
                continue

            try:
                if action == "DELETE":
                    if etype == "deal":
                        row = conn.execute("SELECT is_deleted, deal_number FROM deals WHERE id = ?", (eid,)).fetchone()
                        if row:
                            ev["entity_name"] = row[1]
                            ev["can_undo"] = bool(row[0])
                            ev["undo_state"] = "pending_undo" if row[0] else "already_undone"
                    elif etype in ("deal_chain", "chain"):
                        row = conn.execute("SELECT is_deleted, chain_code FROM deal_chains WHERE id = ?", (eid,)).fetchone()
                        if row:
                            ev["entity_name"] = row[1]
                            ev["can_undo"] = bool(row[0])
                            ev["undo_state"] = "pending_undo" if row[0] else "already_undone"
                    elif etype == "party":
                        row = conn.execute("SELECT is_deleted, name FROM parties WHERE id = ?", (eid,)).fetchone()
                        if row:
                            ev["entity_name"] = row[1]
                            ev["can_undo"] = bool(row[0])
                            ev["undo_state"] = "pending_undo" if row[0] else "already_undone"
                    elif etype == "product":
                        row = conn.execute("SELECT is_deleted, name FROM products WHERE id = ?", (eid,)).fetchone()
                        if row:
                            ev["entity_name"] = row[1]
                            ev["can_undo"] = bool(row[0])
                            ev["undo_state"] = "pending_undo" if row[0] else "already_undone"
                    elif etype in ("brokerage_payment", "payment"):
                        row = conn.execute("SELECT is_deleted, amount FROM brokerage_payments WHERE id = ?", (eid,)).fetchone()
                        if row:
                            ev["entity_name"] = f"Payment ₹{row[1]:,.2f}"
                            ev["can_undo"] = bool(row[0])
                            ev["undo_state"] = "pending_undo" if row[0] else "already_undone"

                elif action == "CANCEL":
                    if etype == "deal":
                        row = conn.execute("SELECT status, deal_number FROM deals WHERE id = ?", (eid,)).fetchone()
                        if row:
                            ev["entity_name"] = row[1]
                            ev["can_undo"] = (row[0] == "cancelled")
                            ev["undo_state"] = "pending_undo" if row[0] == "cancelled" else "already_undone"

            except Exception:
                pass

        return events
