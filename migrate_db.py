import sqlite3
from email_verification import init_email_verification_table
from db_config import DB_FILE as DB_PATH

def migrate(db_path: str = DB_PATH):
    print("Starting database migration...")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # 1) جدول کدهای تایید ایمیل
        init_email_verification_table(conn)
        conn.commit()
        print("✓ Email verifications table checked/created.")

        # 2) ستون email_verified در جدول users
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        if cursor.fetchone() is None:
            print("! Table 'users' not found. Run init_db.py first.")
            return

        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]

        if "email_verified" not in columns:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0"
            )
            conn.commit()
            print("✓ Column 'email_verified' added to 'users'.")
        else:
            print("✓ Column 'email_verified' already exists.")

        if "created_at" not in columns:
            # SQLite در ALTER اجازه‌ی DEFAULT غیرثابت نمی‌دهد، پس دستی پر می‌کنیم
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
            cursor.execute(
                "UPDATE users SET created_at = CURRENT_TIMESTAMP "
                "WHERE created_at IS NULL"
            )
            conn.commit()
            print("✓ Column 'created_at' added to 'users'.")
        else:
            print("✓ Column 'created_at' already exists.")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Migration error: {e}")
    finally:
        conn.close()

    print("Migration finished successfully! 🚀")


if __name__ == "__main__":
    migrate()
