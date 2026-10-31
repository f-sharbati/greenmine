"""
منسوخ شده. schema این فایل با init_db.py تناقض داشت
(نبود inverter_connections و نام ستون plant_name به‌جای name).
برای پرهیز از دو منبع حقیقت، همه‌چیز به init_db.py منتقل شد.
"""

from init_db import setup_database

def init_db():
    print("db_setup.init_db() is deprecated. Delegating to init_db.setup_database().")
    setup_database()

if __name__ == "__main__":
    init_db()
