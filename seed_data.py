import hashlib
import sqlite3
from db_config import DB_FILE as DB_NAME

DEMO_USER = ("mehrava", "my_secret_password", "mehrava@greenmine.com")
DEMO_PLANT = ("Farzanegan Solar Plant", "Tehran, Iran")
DEMO_INVERTER = ("Main KACO Inverter", "KC-987654321", "KACO blueplanet 50.0 TL3")
DEMO_CONNECTION = ("Modbus TCP", "192.168.1.100", 502, "Active")

def _get_or_create_user(cursor) -> int:
    username, password, email = DEMO_USER
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return row[0]

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute(
        "INSERT INTO users (username, password_hash, email, email_verified) "
        "VALUES (?, ?, ?, 1)",
        (username, password_hash, email),
    )
    return cursor.lastrowid

def _get_or_create_plant(cursor, user_id: int) -> int:
    name, location = DEMO_PLANT
    cursor.execute(
        "SELECT plant_id FROM plants WHERE user_id = ? AND name = ?", (user_id, name)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO plants (user_id, name, location) VALUES (?, ?, ?)",
        (user_id, name, location),
    )
    return cursor.lastrowid

def _get_or_create_inverter(cursor, plant_id: int) -> int:
    name, serial_number, model = DEMO_INVERTER
    cursor.execute(
        "SELECT inverter_id FROM inverters WHERE serial_number = ?", (serial_number,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO inverters (plant_id, name, serial_number, model) "
        "VALUES (?, ?, ?, ?)",
        (plant_id, name, serial_number, model),
    )
    return cursor.lastrowid

def _get_or_create_connection(cursor, inverter_id: int) -> int:
    connection_type, ip_address, port, status = DEMO_CONNECTION
    cursor.execute(
        "SELECT connection_id FROM inverter_connections "
        "WHERE inverter_id = ? AND ip_address = ?",
        (inverter_id, ip_address),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO inverter_connections "
        "(inverter_id, connection_type, ip_address, port, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (inverter_id, connection_type, ip_address, port, status),
    )
    return cursor.lastrowid


def seed_database(db_name: str = DB_NAME):
    conn = sqlite3.connect(db_name)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        user_id = _get_or_create_user(cursor)
        plant_id = _get_or_create_plant(cursor, user_id)
        inverter_id = _get_or_create_inverter(cursor, plant_id)
        connection_id = _get_or_create_connection(cursor, inverter_id)

        conn.commit()
        print(
            "داده‌های پایه آماده شد "
            f"(user={user_id}, plant={plant_id}, "
            f"inverter={inverter_id}, connection={connection_id})"
        )

    except sqlite3.Error as e:
        conn.rollback()
        print(f"خطای دیتابیسی: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_database()
