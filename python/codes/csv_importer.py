import sqlite3
import pandas as pd
import os

def import_csv_to_db(csv_filename):
    if not os.path.exists(csv_filename):
        print(f" خطا: فایل {csv_filename} پیدا نشد!")
        return

    print(f" در حال خواندن فایل {csv_filename}...")
    
    df = pd.read_csv(csv_filename)

    df_clean = df.dropna(subset=['date'])

    # اتصال به دیتابیس
    conn = sqlite3.connect('greenmine.db')
    cursor = conn.cursor()

    try:
        count = 0
        for index, row in df_clean.iterrows():
            inverter_id = 1 
            date = row['date']
            daily_yield = row['yield']

            cursor.execute('''
            INSERT INTO production_readings (inverter_id, date, daily_yield)
            VALUES (?, ?, ?)
            ''', (inverter_id, date, daily_yield))
            count += 1

        conn.commit()
        print(f"✅ موفقیت! {count} ردیف داده با موفقیت به دیتابیس اضافه شد.")

    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    import_csv_to_db('1.CSV')
