import hashlib
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# EMAIL / SMTP CONFIG
_SMTP_DEFAULTS = {
    "enabled": False,
    "server": "smtp.gmail.com",
    "port": 587,
    "use_tls": True,
    "sender_email": "",
    "app_password": "",
    "sender_name": "GreenMine",
}

def _load_smtp_config() -> dict:
    cfg = dict(_SMTP_DEFAULTS)

    try:
        import streamlit as st
        raw = dict(st.secrets.get("smtp", {}))
    except Exception:
        raw = {}

    for key in _SMTP_DEFAULTS:
        if key in raw and raw[key] not in (None, ""):
            cfg[key] = raw[key]

    cfg["enabled"] = bool(cfg["enabled"])
    cfg["use_tls"] = bool(cfg["use_tls"])

    try:
        cfg["port"] = int(cfg["port"])
    except (TypeError, ValueError):
        cfg["port"] = 587

    return cfg

# OTP / SECURITY SETTINGS
CODE_LENGTH = 6
CODE_TTL_MINUTES = 10
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60
DELETE_EXPIRED_AFTER_DAYS = 30

# TIME HELPERS
def utc_now():
    return datetime.now(timezone.utc)

def to_iso(dt: datetime) -> str:
    return dt.isoformat()

def parse_datetime(dt_str: str) -> datetime:
    """
    Parse SQLite / ISO datetime safely.
    """
    if not dt_str:
        raise ValueError("Empty datetime string")

    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError(f"Unsupported datetime format: {dt_str}")

# HASH / CODE HELPERS
def generate_verification_code() -> str:
    upper = 10 ** CODE_LENGTH
    return f"{secrets.randbelow(upper):0{CODE_LENGTH}d}"


def hash_code(code: str) -> str:
    return hashlib.sha256(str(code).encode("utf-8")).hexdigest()

# DB SCHEMA
def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_def: str,
):
    """
    Add column if it does not exist.
    """
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {row[1] for row in rows}

    if column_name not in existing_columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        )


def init_email_verification_table(conn: sqlite3.Connection):
    """
    Create email_verifications table + indexes if missing,
    with light schema healing.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS email_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            verified_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sent_at TEXT,
            delivery_status TEXT DEFAULT 'pending',
            last_error TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_email_verifications_user_id
        ON email_verifications(user_id)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_email_verifications_email
        ON email_verifications(email)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_email_verifications_verified_at
        ON email_verifications(verified_at)
        """
    )

    _ensure_column(conn, "email_verifications", "sent_at", "TEXT")
    _ensure_column(
        conn,
        "email_verifications",
        "delivery_status",
        "TEXT DEFAULT 'pending'",
    )
    _ensure_column(conn, "email_verifications", "last_error", "TEXT")

    conn.commit()

# MAINTENANCE
def cleanup_old_verification_requests(conn: sqlite3.Connection):
    """
    Delete old expired or long-verified rows.
    """
    init_email_verification_table(conn)

    cutoff_iso = to_iso(utc_now() - timedelta(days=DELETE_EXPIRED_AFTER_DAYS))

    conn.execute(
        """
        DELETE FROM email_verifications
        WHERE
            (verified_at IS NOT NULL AND verified_at < ?)
            OR
            (verified_at IS NULL AND expires_at < ?)
        """,
        (cutoff_iso, cutoff_iso),
    )

    conn.commit()

def invalidate_previous_requests(conn: sqlite3.Connection, user_id: int):
    """
    Expire older unverified requests so only the latest OTP is valid.
    """
    init_email_verification_table(conn)

    now_iso = to_iso(utc_now())

    conn.execute(
        """
        UPDATE email_verifications
        SET expires_at = ?
        WHERE user_id = ?
          AND verified_at IS NULL
        """,
        (now_iso, user_id),
    )

    conn.commit()

# EMAIL SENDING
def is_email_sending_configured() -> bool:
    cfg = _load_smtp_config()

    return all(
        [
            cfg["enabled"],
            cfg["server"],
            cfg["port"],
            cfg["sender_email"],
            cfg["app_password"],
        ]
    )

def send_verification_email(recipient_email: str, code: str) -> tuple[bool, str]:
    """
    Send verification email.

    Returns:
        (True, "sent")
        (False, "error message")
    """
    cfg = _load_smtp_config()

    if not is_email_sending_configured():
        return False, "SMTP تنظیم نشده است. secrets.toml را بررسی کنید."

    body = f"""
سلام!

کد تأیید ایمیل شما در GreenMine:

{code}

این کد تا {CODE_TTL_MINUTES} دقیقه معتبر است.

اگر این درخواست از طرف شما نبوده، این ایمیل را نادیده بگیرید.

با احترام
GreenMine
""".strip()

    msg = MIMEMultipart()
    msg["From"] = f"{cfg['sender_name']} <{cfg['sender_email']}>"
    msg["To"] = recipient_email
    msg["Subject"] = "GreenMine Verification Code"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    server = None

    try:
        server = smtplib.SMTP(cfg["server"], cfg["port"], timeout=20)

        if cfg["use_tls"]:
            server.starttls()

        server.login(cfg["sender_email"], cfg["app_password"])
        server.sendmail(cfg["sender_email"], recipient_email, msg.as_string())

        return True, "sent"

    except Exception as e:
        return False, str(e)

    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass

# REQUEST RATE LIMIT
def can_request_new_code(
    conn: sqlite3.Connection,
    user_id: int,
) -> tuple[bool, str]:
    """
    Prevent spammy repeated OTP requests.
    """
    init_email_verification_table(conn)

    row = conn.execute(
        """
        SELECT created_at
        FROM email_verifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if row is None:
        return True, "OK"

    created_at_value = row["created_at"] if isinstance(row, sqlite3.Row) else row[0]

    try:
        last_created = parse_datetime(created_at_value)
    except Exception:
        return True, "OK"

    diff = (utc_now() - last_created).total_seconds()

    if diff < RESEND_COOLDOWN_SECONDS:
        remain = int(RESEND_COOLDOWN_SECONDS - diff)
        return False, f"لطفاً {remain} ثانیه دیگر دوباره تلاش کنید."

    return True, "OK"

# CORE API - COMPATIBLE WITH proj1.py
def create_verification_request(
    conn: sqlite3.Connection,
    user_id: int,
    email: str,
) -> str:
    """
    Create a new OTP request and return raw code.

    Compatible with current proj1.py:
        code = email_verification.create_verification_request(conn, user_id, email)

    Behavior:
    - creates table if needed
    - rate-limits repeated requests
    - invalidates older active codes
    - stores only code hash
    - tries to send email if SMTP is configured
    - returns the raw code for optional demo/debug flows
    """
    init_email_verification_table(conn)
    cleanup_old_verification_requests(conn)

    allowed, msg = can_request_new_code(conn, user_id)

    if not allowed:
        raise ValueError(msg)

    invalidate_previous_requests(conn, user_id)

    code = generate_verification_code()
    code_hash = hash_code(code)
    expires_at = to_iso(utc_now() + timedelta(minutes=CODE_TTL_MINUTES))

    cursor = conn.execute(
        """
        INSERT INTO email_verifications
            (user_id, email, code_hash, expires_at, attempts, delivery_status)
        VALUES (?, ?, ?, ?, 0, 'pending')
        """,
        (user_id, email, code_hash, expires_at),
    )

    verification_id = cursor.lastrowid

    conn.commit()

    if is_email_sending_configured():
        success, result = send_verification_email(email, code)

        if success:
            conn.execute(
                """
                UPDATE email_verifications
                SET sent_at = ?,
                    delivery_status = 'sent',
                    last_error = NULL
                WHERE id = ?
                """,
                (to_iso(utc_now()), verification_id),
            )
        else:
            conn.execute(
                """
                UPDATE email_verifications
                SET delivery_status = 'failed',
                    last_error = ?
                WHERE id = ?
                """,
                (result, verification_id),
            )

        conn.commit()

    return code


def verify_code(
    conn: sqlite3.Connection,
    user_id: int,
    input_code: str,
) -> tuple[bool, str]:
    """
    Verify latest active code for user.

    Compatible with current proj1.py:
        success, msg = email_verification.verify_code(conn, user_id, otp_input)
    """
    init_email_verification_table(conn)

    if input_code is None:
        return False, "کد وارد نشده است."

    input_code = str(input_code).strip()

    if not input_code:
        return False, "کد وارد نشده است."

    row = conn.execute(
        """
        SELECT id, code_hash, expires_at, attempts
        FROM email_verifications
        WHERE user_id = ?
          AND verified_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if row is None:
        return False, "درخواست تأیید فعالی پیدا نشد."

    row_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]
    code_hash_db = row["code_hash"] if isinstance(row, sqlite3.Row) else row[1]
    expires_at_raw = row["expires_at"] if isinstance(row, sqlite3.Row) else row[2]
    attempts = row["attempts"] if isinstance(row, sqlite3.Row) else row[3]

    if attempts >= MAX_ATTEMPTS:
        return False, "تعداد تلاش‌های مجاز به پایان رسیده است."

    conn.execute(
        """
        UPDATE email_verifications
        SET attempts = attempts + 1
        WHERE id = ?
        """,
        (row_id,),
    )

    conn.commit()

    try:
        expires_at = parse_datetime(expires_at_raw)
    except ValueError:
        return False, "زمان انقضای کد نامعتبر است."

    if utc_now() > expires_at:
        return False, "کد منقضی شده است."

    if hash_code(input_code) != code_hash_db:
        remaining = max(0, MAX_ATTEMPTS - (attempts + 1))

        if remaining == 0:
            return False, "کد اشتباه بود و تعداد تلاش‌های مجاز به پایان رسید."

        return False, f"کد واردشده اشتباه است. {remaining} تلاش باقی مانده."

    now_iso = to_iso(utc_now())

    conn.execute(
        """
        UPDATE email_verifications
        SET verified_at = ?,
            delivery_status = 'verified'
        WHERE id = ?
        """,
        (now_iso, row_id),
    )

    conn.execute(
        """
        UPDATE users
        SET email_verified = 1
        WHERE id = ?
        """,
        (user_id,),
    )

    conn.commit()

    return True, "ایمیل با موفقیت تأیید شد!"

# OPTIONAL EXTRA HELPERS
def resend_verification_code(
    conn: sqlite3.Connection,
    user_id: int,
    email: str,
) -> str:
    """
    Simple wrapper for requesting a fresh code again.
    Keeps compatibility and reuses all checks.
    """
    return create_verification_request(conn, user_id, email)

def get_latest_verification_status(
    conn: sqlite3.Connection,
    user_id: int,
) -> dict:
    """
    Helpful for debugging/admin panels.
    """
    init_email_verification_table(conn)

    row = conn.execute(
        """
        SELECT id,
               email,
               expires_at,
               attempts,
               verified_at,
               created_at,
               sent_at,
               delivery_status,
               last_error
        FROM email_verifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if row is None:
        return {
            "exists": False,
            "message": "No verification request found.",
        }

    def val(key, index):
        return row[key] if isinstance(row, sqlite3.Row) else row[index]

    return {
        "exists": True,
        "id": val("id", 0),
        "email": val("email", 1),
        "expires_at": val("expires_at", 2),
        "attempts": val("attempts", 3),
        "verified_at": val("verified_at", 4),
        "created_at": val("created_at", 5),
        "sent_at": val("sent_at", 6),
        "delivery_status": val("delivery_status", 7),
        "last_error": val("last_error", 8),
    }
