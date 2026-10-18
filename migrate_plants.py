# اضافه‌کردن ستون‌های فنی به جدول plants بدون حذف داده‌ی موجود
import sqlite3
from db_config import DB_FILE

NEW_COLUMNS = {
    "capacity_ac":       "REAL",     # ظرفیت اسمی AC (kW)
    "capacity_dc":       "REAL",     # ظرفیت اسمی DC (kWp)
    "utm_easting":       "REAL",     # مختصات UTM - Easting
    "utm_northing":      "REAL",     # مختصات UTM - Northing
    "utm_zone":          "TEXT",     # مثلا "39N"
    "latitude":          "REAL",     # عرض جغرافیایی
    "longitude":         "REAL",     # طول جغرافیایی
    "tilt":              "REAL",     # زاویه نصب پنل (درجه)
    "azimuth":           "REAL",     # جهت پنل (درجه، ۱۸۰=رو به جنوب)
    "performance_ratio": "REAL",     # ضریب عملکرد PR (0..1)
    "panel_type":        "TEXT",     # نوع پنل (Mono / Poly / Bifacial ...)
    "mount_type":        "TEXT",     # نوع نصب (Fixed / Tracker ...)
    "info_completed":    "INTEGER DEFAULT 0",  # آیا فرم کامل شده؟
}

def migrate():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # ستون‌های موجود را می‌گیریم
    cur.execute("PRAGMA table_info(plants)")
    existing = {row[1] for row in cur.fetchall()}

    added = []
    for col, col_def in NEW_COLUMNS.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE plants ADD COLUMN {col} {col_def}")
            added.append(col)

    conn.commit()
    conn.close()

    if added:
        print("Added columns:", ", ".join(added))
    else:
        print("No changes needed. All columns already exist.")

if __name__ == "__main__":
    migrate()
