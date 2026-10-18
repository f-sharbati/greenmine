import sqlite3
from db_config import DB_FILE as DB_NAME

def setup_database(db_name: str = DB_NAME, with_email_verification: bool = True):
    """
    منبع واحد حقیقت برای ساخت دیتابیس GreenMine.
    هشدار: این تابع جدول‌های موجود را DROP می‌کند (ساخت تمیز).
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    print("Rebuilding GreenMine database...")

    cursor.execute("DROP TABLE IF EXISTS production_readings")
    cursor.execute("DROP TABLE IF EXISTS inverter_connections")
    cursor.execute("DROP TABLE IF EXISTS inverters")
    cursor.execute("DROP TABLE IF EXISTS plants")
    cursor.execute("DROP TABLE IF EXISTS email_verifications")
    cursor.execute("DROP TABLE IF EXISTS users")

    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute("""
    CREATE TABLE users (
        user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        username       TEXT UNIQUE NOT NULL,
        password_hash  TEXT NOT NULL,
        email          TEXT UNIQUE,
        email_verified INTEGER NOT NULL DEFAULT 0,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # جدول نیروگاه‌ها
    cursor.execute("""
    CREATE TABLE plants (
        plant_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        name       TEXT NOT NULL,
        location   TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # جدول اینورترها
    cursor.execute("""
    CREATE TABLE inverters (
        inverter_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id      INTEGER NOT NULL,
        name          TEXT NOT NULL,
        serial_number TEXT,
        model         TEXT,
        brand         TEXT DEFAULT 'KACO',
        FOREIGN KEY (plant_id) REFERENCES plants(plant_id)
    )
    """)

    # جدول اتصال اینورتر
    cursor.execute("""
    CREATE TABLE inverter_connections (
        connection_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        inverter_id     INTEGER NOT NULL,
        connection_type TEXT,
        ip_address      TEXT,
        port            INTEGER,
        status          TEXT,
        FOREIGN KEY (inverter_id) REFERENCES inverters(inverter_id)
    )
    """)

    # جدول داده‌های تولید
    cursor.execute("""
    CREATE TABLE production_readings (
        reading_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        inverter_id INTEGER NOT NULL,
        date        TEXT NOT NULL,
        daily_yield REAL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(inverter_id, date),
        FOREIGN KEY (inverter_id) REFERENCES inverters(inverter_id)
    )
    """)

    conn.commit()

    # جدول کدهای تأیید ایمیل
    if with_email_verification:
        try:
            from email_verification import init_email_verification_table
            init_email_verification_table(conn)
            conn.commit()
            print("✓ email_verifications table created.")
        except ImportError:
            print("! email_verification module not found; skipped that table.")

    conn.close()
    print("Database created successfully! ✅")

if __name__ == "__main__":
    answer = input(f"This will ERASE all data in '{DB_NAME}'. Continue? (yes/no): ")
    if answer.strip().lower() in {"yes", "y"}:
        setup_database()
    else:
        print("Aborted. Nothing was changed.")
