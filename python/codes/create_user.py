import argparse
import hashlib
import sqlite3

from db_config import DB_FILE as DB_NAME

def create_user(username: str, password: str, email: str,
                db_name: str = DB_NAME) -> bool:
    if not username or not password:
        print("خطا: نام کاربری و رمز نمی‌توانند خالی باشند.")
        return False

    conn = sqlite3.connect(db_name)
    try:
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email),
        )
        conn.commit()
        print(f"کاربر '{username}' با موفقیت ساخته شد! ✅")
        return True

    except sqlite3.IntegrityError as e:
        detail = str(e).lower()
        if "email" in detail:
            print(f"خطا: ایمیل '{email}' قبلاً ثبت شده است.")
        elif "username" in detail:
            print(f"خطا: نام کاربری '{username}' قبلاً وجود دارد.")
        else:
            print(f"خطای یکتایی: {e}")
        return False

    except sqlite3.OperationalError as e:
        print(f"خطا: جدول users آماده نیست ({e}). ابتدا init_db.py را اجرا کن.")
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a GreenMine user.")
    parser.add_argument("--username", default="mehrava")
    parser.add_argument("--password", default="my_secret_password")
    parser.add_argument("--email", default="mehrava@greenmine.com")
    args = parser.parse_args()

    create_user(args.username, args.password, args.email)
