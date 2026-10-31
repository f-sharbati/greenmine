# برای اجرای پروؤه کد "streamlit run proj1.py" را در ترمیتال بنویسید.

import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import json
import uuid
import email_verification
import os
import time
from db_config import DB_FILE
import random
from dashboard_view import render_dashboard
import i18n
import datetime

# GreenMine Demo Carbon Token (DemoCT) — Demo Settings
DEFAULT_GRID_EMISSION_FACTOR = 0.66   # kg CO2 / kWh
CAR_CO2_PER_KM_G = 148.0              # grams CO2 / km
DEFAULT_TOKEN_UNIT_KG = 10.0          # 1 DemoCT = 10 kg CO2 avoided
TOKEN_SYMBOL = "DemoCT"
CALCULATION_VERSION = "v1.2-democt"
CARBON_TOKEN_UNIT_KG = 10.0
CARBON_TOKEN_SYMBOL = "DemoCT"

# DATABASE CONFIG
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

#PLANT FIELDS
REQUIRED_PLANT_FIELDS = [
    "name", "capacity_ac",
    "utm_easting", "utm_northing", "utm_zone",
    "tilt", "azimuth", "performance_ratio",
    "panel_type", "mount_type",
]

AZIMUTH_DIRECTIONS = {
    "North (شمال)": 0,
    "Northeast (شمال شرقی)": 45,
    "East (شرق)": 90,
    "Southeast (جنوب شرقی)": 135,
    "South (جنوب)": 180,
    "Southwest (جنوب غربی)": 225,
    "West (غرب)": 270,
    "Northwest (شمال غربی)": 315,
}

def get_user_plant(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM plants WHERE user_id = ? ORDER BY id LIMIT 1",
            (user_id,),
        ).fetchone()
        return row
    finally:
        conn.close()

def is_plant_info_complete(user_id):
    plant = get_user_plant(user_id)
    if plant is None:
        return False
    keys = plant.keys()
    for field in REQUIRED_PLANT_FIELDS:
        if field not in keys:
            return False
        value = plant[field]
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
    return True

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None

def get_table_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    return [row[1] for row in rows]

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS
    if table_exists(cursor, "users"):
        user_cols = get_table_columns(cursor, "users")
        expected_user_cols = {
            "id", "username", "password", "full_name", "email", "email_verified"
        }
        if not expected_user_cols.issubset(set(user_cols)):
            cursor.execute("DROP TABLE IF EXISTS users")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE,
            email_verified INTEGER DEFAULT 0
        )
        """
    )

    #PLANTS
    if table_exists(cursor, "plants"):
        plant_cols = get_table_columns(cursor, "plants")
        expected_plant_cols = {
            "id", "user_id", "name", "location",
            "capacity_ac", "utm_easting", "utm_northing", "utm_zone",
            "tilt", "azimuth", "performance_ratio",
            "panel_type", "mount_type", "info_completed",
        }
        if not expected_plant_cols.issubset(set(plant_cols)):
            cursor.execute("DROP TABLE IF EXISTS plants")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            location TEXT,
            capacity_ac REAL,
            utm_easting REAL,
            utm_northing REAL,
            utm_zone TEXT,
            tilt REAL,
            azimuth REAL,
            performance_ratio REAL,
            panel_type TEXT,
            mount_type TEXT,
            info_completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    #INVERTERS
    if table_exists(cursor, "inverters"):
        inverter_cols = get_table_columns(cursor, "inverters")
        expected_inverter_cols = {"id", "plant_id", "serial_number", "model"}
        if not expected_inverter_cols.issubset(set(inverter_cols)):
            cursor.execute("DROP TABLE IF EXISTS inverters")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inverters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id INTEGER,
            serial_number TEXT UNIQUE NOT NULL,
            model TEXT,
            FOREIGN KEY (plant_id) REFERENCES plants(id)
        )
        """
    )

    #PRODUCTION READINGS
    if table_exists(cursor, "production_readings"):
        reading_cols = get_table_columns(cursor, "production_readings")
        expected_reading_cols = {"id", "inverter_id", "reading_date", "daily_yield"}
        if not expected_reading_cols.issubset(set(reading_cols)):
            cursor.execute("DROP TABLE IF EXISTS production_readings")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS production_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inverter_id INTEGER,
            reading_date TEXT NOT NULL,
            daily_yield REAL NOT NULL,
            FOREIGN KEY (inverter_id) REFERENCES inverters(id)
        )
        """
    )

    #CARBON CERTIFICATES
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS carbon_certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plant_id INTEGER NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            energy_kwh REAL NOT NULL,
            emission_factor REAL NOT NULL,
            co2_saved_kg REAL NOT NULL,
            token_unit_kg REAL NOT NULL,
            token_count INTEGER NOT NULL,
            remainder_kg REAL NOT NULL,
            certificate_code TEXT UNIQUE NOT NULL,
            token_status TEXT NOT NULL DEFAULT 'demo',
            calculation_version TEXT NOT NULL DEFAULT 'v1.2-democt',
            metadata_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (plant_id) REFERENCES plants(id)
        )
        """
    )

    #EMAIL VERIFICATIONS
    email_verification.init_email_verification_table(conn)

    cursor.execute(
        """
        DELETE FROM production_readings
        WHERE reading_date IS NULL
           OR TRIM(reading_date) = ''
           OR LOWER(TRIM(reading_date)) IN ('nan', 'none', 'null', 'summary', 'total')
        """
    )

    conn.commit()
    conn.close()

init_db()

# DATA CLEANING
def clean_uploaded_csv(df):
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    if "date" not in df.columns or "yield" not in df.columns:
        raise ValueError("CSV must contain 'date' and 'yield' columns.")

    df = df[["date", "yield"]].copy()

    df["date"] = df["date"].astype(str).str.strip()
    df["yield"] = df["yield"].astype(str).str.replace(",", "", regex=False).str.strip()

    bad_tokens = {"", "nan", "none", "null", "summary", "total"}
    df = df[~df["date"].str.lower().isin(bad_tokens)]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["yield"] = pd.to_numeric(df["yield"], errors="coerce")

    df = df.dropna(subset=["date", "yield"])

    if not df.empty:
        median_yield = df["yield"].median()
        df = df[df["yield"] < (median_yield * 5)]

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["yield"] = df["yield"] / 1000.0
    df = df.drop_duplicates(subset=["date"], keep="first").reset_index(drop=True)

    return df

# USER FUNCTIONS
def register_user(username, password, full_name, email):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        hashed_pw = make_hashes(password)

        cursor.execute(
            """
            INSERT INTO users (username, password, full_name, email, email_verified)
            VALUES (?, ?, ?, ?, 0)
            """,
            (username, hashed_pw, full_name, email),
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO plants (user_id, name, location)
            VALUES (?, ?, ?)
            """,
            (user_id, "Default Solar Plant", "Tehran"),
        )
        plant_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO inverters (plant_id, serial_number, model)
            VALUES (?, ?, ?)
            """,
            (plant_id, f"INV-{username.upper()}-01", "GreenMine-v1"),
        )

        conn.commit()
        return True, "Account created successfully. Please log in."
    except sqlite3.IntegrityError as e:
        conn.rollback()
        msg = str(e)
        if "users.email" in msg:
            return False, "This email is already registered. Try logging in or use another email."
        if "users.username" in msg:
            return False, "This username is already taken. Please choose another one."
        return False, "Registration failed. Please check your information and try again."
    except Exception:
        conn.rollback()
        return False, "Unexpected error during registration. Please try again later."
    finally:
        conn.close()

def generate_captcha():
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    st.session_state["captcha_a"] = a
    st.session_state["captcha_b"] = b
    st.session_state["captcha_answer"] = a + b

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_hashes(password, user["password"]):
        return user
    return None

def login_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def get_user_data(user_id):
    conn = get_db_connection()
    query = """
        SELECT r.reading_date, r.daily_yield
        FROM production_readings r
        JOIN inverters i ON r.inverter_id = i.id
        JOIN plants p ON i.plant_id = p.id
        WHERE p.user_id = ?
          AND r.reading_date IS NOT NULL
          AND TRIM(r.reading_date) <> ''
          AND LOWER(TRIM(r.reading_date)) NOT IN ('nan', 'none', 'null', 'summary', 'total')
        ORDER BY r.reading_date ASC
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df

def save_readings_to_db(df_to_save, user_id):
    if df_to_save is None or df_to_save.empty:
        return False, "No valid daily rows found in CSV."

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT i.id
            FROM inverters i
            JOIN plants p ON i.plant_id = p.id
            WHERE p.user_id = ?
            LIMIT 1
            """,
            (user_id,),
        )
        inv_row = cursor.fetchone()

        if not inv_row:
            return False, "Inverter not found."

        inverter_id = inv_row["id"]
        inserted = 0
        skipped = 0

        for _, row in df_to_save.iterrows():
            cursor.execute(
                """
                SELECT id
                FROM production_readings
                WHERE inverter_id = ? AND reading_date = ?
                """,
                (inverter_id, row["date"]),
            )
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(
                    """
                    INSERT INTO production_readings (inverter_id, reading_date, daily_yield)
                    VALUES (?, ?, ?)
                    """,
                    (inverter_id, row["date"], float(row["yield"])),
                )
                inserted += 1
            else:
                skipped += 1

        conn.commit()
        return True, f"Successfully imported {inserted} new records! Skipped {skipped} duplicates."

    except Exception as e:
        conn.rollback()
        return False, f"Error saving readings: {e}"

    finally:
        conn.close()

# Carbon Calculation Helpers
def calculate_carbon_tokens(
    energy_kwh,
    emission_factor=DEFAULT_GRID_EMISSION_FACTOR,
    token_unit_kg=CARBON_TOKEN_UNIT_KG,
):
    co2_saved_kg = float(energy_kwh) * float(emission_factor)
    token_count = int(co2_saved_kg // token_unit_kg)
    remainder_kg = co2_saved_kg % token_unit_kg
    return co2_saved_kg, token_count, remainder_kg

def get_mint_summary(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COALESCE(SUM(energy_kwh), 0), COALESCE(SUM(token_count), 0)
            FROM carbon_certificates
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        return (float(row[0]), int(row[1])) if row else (0.0, 0)
    except sqlite3.Error:
        return 0.0, 0
    finally:
        conn.close()

def record_mint(
    user_id: int,
    energy_kwh: float,
    token_count: int,
    plant_id: int | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    emission_factor: float = DEFAULT_GRID_EMISSION_FACTOR,
):
    if token_count <= 0:
        return False, "Nothing to mint."

    co2_saved_kg = float(energy_kwh) * float(emission_factor)
    remainder_kg = max(0.0, co2_saved_kg - (int(token_count) * CARBON_TOKEN_UNIT_KG))
    cert_code = f"GM-{user_id}-{uuid.uuid4().hex[:8].upper()}"

    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()

        if plant_id is None:
            row = cur.execute(
                "SELECT id FROM plants WHERE user_id = ? ORDER BY id LIMIT 1",
                (user_id,),
            ).fetchone()
            if row is None:
                return False, "No plant found for this user."
            plant_id = row[0]

        if period_start is None or period_end is None:
            today = datetime.date.today().isoformat()
            rng = None
            try:
                cols = {
                    r[1]
                    for r in cur.execute(
                        "PRAGMA table_info(production_readings)"
                    ).fetchall()
                }
                date_col = "reading_date" if "reading_date" in cols else "date"

                rng = cur.execute(
                    f"""
                    SELECT MIN(pr.{date_col}), MAX(pr.{date_col})
                    FROM production_readings pr
                    JOIN inverters i ON i.id = pr.inverter_id
                    WHERE i.plant_id = ?
                    """,
                    (plant_id,),
                ).fetchone()
            except sqlite3.Error:
                rng = None  

            period_start = period_start or (rng[0] if rng and rng[0] else today)
            period_end = period_end or (rng[1] if rng and rng[1] else today)

        cur.execute(
            """
            INSERT INTO carbon_certificates
                (user_id, plant_id, period_start, period_end,
                 energy_kwh, emission_factor, co2_saved_kg,
                 token_unit_kg, token_count, remainder_kg,
                 certificate_code, token_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'demo')
            """,
            (
                user_id,
                int(plant_id),
                str(period_start),
                str(period_end),
                float(energy_kwh),
                float(emission_factor),
                float(co2_saved_kg),
                float(CARBON_TOKEN_UNIT_KG),
                int(token_count),
                float(remainder_kg),
                cert_code,
            ),
        )
        conn.commit()
        return True, cert_code
    except sqlite3.Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def generate_certificate_code():
    return f"GM-CERT-{uuid.uuid4().hex[:12].upper()}"

def get_user_primary_plant_id(conn, user_id):
    row = conn.execute(
        """
        SELECT id
        FROM plants
        WHERE user_id = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return row["id"] if row else None

def get_user_primary_plant_name(conn, user_id):
    row = conn.execute(
        """
        SELECT name
        FROM plants
        WHERE user_id = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return row["name"] if row else "Default Solar Plant"

def get_user_certificates(conn, user_id):
    return conn.execute(
        """
        SELECT *
        FROM carbon_certificates
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()

# STREAMLIT PAGE CONFIG
st.set_page_config(
    page_title="GreenMine Dashboard",
    page_icon="🌱",
    layout="wide",
)

i18n.init()
i18n.apply_direction()

# HEADER
st.markdown(
    "<h1 style='text-align: center; color: #2E7D32;'>GreenMine Carbon Credit Tracker</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #558B2F;'>Designed & Developed by <b>Mehrava Sharbati</b></p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# SESSION STATE
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "full_name" not in st.session_state:
    st.session_state["full_name"] = ""
if "pending_verification" not in st.session_state:
    st.session_state["pending_verification"] = False
if "temp_user_id" not in st.session_state:
    st.session_state["temp_user_id"] = None
if "temp_email" not in st.session_state:
    st.session_state["temp_email"] = ""
if "last_otp" not in st.session_state:
    st.session_state["last_otp"] = ""
if "nav_override" not in st.session_state:
    st.session_state["nav_override"] = None
if "captcha_answer" not in st.session_state:
    generate_captcha()

PAGE_LABEL_KEYS = {
    "Home":       "nav.home",
    "Login":      "nav.login",
    "Register":   "nav.register",
    "Plant Info": "nav.plant_info",
    "Dashboard":  "nav.dashboard",
    "Logout":     "nav.logout",
}
def page_label(page):
    return i18n.t(PAGE_LABEL_KEYS.get(page, page))

# SIDEBAR MENU
i18n.init()
i18n.language_selector()
i18n.apply_direction()
if st.session_state["logged_in"]:
    menu = ["Home", "Plant Info", "Dashboard", "Logout"]
else:
    menu = ["Home", "Login", "Register"]

#apply pending navigation override BEFORE building the widget
if st.session_state["nav_override"] in menu:
    st.session_state["nav_menu"] = st.session_state["nav_override"]
    st.session_state["nav_override"] = None

#Forced redirect if plant info is incomplete
if st.session_state["logged_in"] and not is_plant_info_complete(st.session_state["user_id"]):
    st.sidebar.warning(i18n.t("nav.incomplete_info"))
    choice = "Plant Info"
    st.sidebar.selectbox(i18n.t("nav.menu"), ["Plant Info"], disabled=True,
                         format_func=page_label, key="nav_menu_locked")
else:
    choice = st.sidebar.selectbox(i18n.t("nav.menu"), menu, key="nav_menu",
                                  format_func=page_label)

# HOME
if choice == "Home":
    st.subheader("Welcome to GreenMine")

    if not st.session_state["logged_in"]:
        st.info("Please login or register from the sidebar to access your personalized dashboard.")
    else:
        st.success(f"Logged in as: {st.session_state['full_name']} ({st.session_state['username']})")

        user_data = get_user_data(st.session_state["user_id"])

        plot_df = user_data.copy()
        if not plot_df.empty:
            plot_df["reading_date"] = pd.to_datetime(plot_df["reading_date"], errors="coerce")
            plot_df = plot_df.dropna(subset=["reading_date"]).sort_values("reading_date")

        if not plot_df.empty:
            total_yield = plot_df["daily_yield"].sum()
            avg_yield = plot_df["daily_yield"].mean()

            co2_reduced_kg = total_yield * DEFAULT_GRID_EMISSION_FACTOR
            co2_reduced_tons = co2_reduced_kg / 1000.0

            equivalent_trees = co2_reduced_kg / 22.0
            ev_distance_km = total_yield * 5.0
            household_days = total_yield / 10.0

            # Distance a gasoline car must drive to emit the CO2 we avoided
            gasoline_car_km = co2_reduced_kg * 1000.0 / CAR_CO2_PER_KM_G

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total Production", f"{total_yield:,.1f} kWh")
            kpi2.metric("Daily Average", f"{avg_yield:,.1f} kWh")
            kpi3.metric("CO₂ Reduced", f"{co2_reduced_tons:,.2f} tons")

            #Carbon Tokens (DemoCT) — demo mint
            minted_kwh, minted_tokens = get_mint_summary(st.session_state["user_id"])
            available_kwh = max(0.0, total_yield - minted_kwh)
            co2_saved_kg, token_count, remainder_kg = calculate_carbon_tokens(
                available_kwh,
                emission_factor=DEFAULT_GRID_EMISSION_FACTOR,
                token_unit_kg=CARBON_TOKEN_UNIT_KG,
            )

            st.markdown("---")
            st.markdown(f"### 🪙 Carbon Tokens ({CARBON_TOKEN_SYMBOL})")

            tok1, tok2, tok3, tok4 = st.columns(4)
            tok1.metric("Mintable Now", f"{token_count:,} {CARBON_TOKEN_SYMBOL}")
            tok2.metric("Already Minted", f"{minted_tokens:,} {CARBON_TOKEN_SYMBOL}")
            tok3.metric("CO₂ Basis (unminted)", f"{co2_saved_kg:,.2f} kg")
            tok4.metric("Remainder", f"{remainder_kg:,.2f} kg")

            st.caption(
                f"1 {CARBON_TOKEN_SYMBOL} = {CARBON_TOKEN_UNIT_KG:,.0f} kg CO₂ avoided · "
                f"emission factor {DEFAULT_GRID_EMISSION_FACTOR} kg/kWh · {CALCULATION_VERSION}"
            )

            mint_col, bal_col = st.columns([1, 3])
            with mint_col:
                mint_clicked = st.button(
                    f"🪙 Mint {token_count:,} {CARBON_TOKEN_SYMBOL}",
                    disabled=token_count <= 0,
                    use_container_width=True,
                )
            with bal_col:
                st.info(
                    f"Ledger balance: {minted_tokens:,} {CARBON_TOKEN_SYMBOL} "
                    f"({minted_kwh:,.2f} kWh locked) — demo mode, no on-chain transaction."
                 )

                if mint_clicked:
                    energy_to_lock = (
                        token_count * CARBON_TOKEN_UNIT_KG
                        / DEFAULT_GRID_EMISSION_FACTOR
                    )
                    ok, info = record_mint(
                        st.session_state["user_id"],
                        energy_to_lock,
                        token_count,
                    )
            imp_col1, imp_col2, imp_col3, imp_col4 = st.columns(4)
            with imp_col1:
                st.markdown(
                    f"""
                    <div style='background:linear-gradient(135deg,#12191f 0%,#0b1116 100%); padding:20px; border-radius:14px; border-left:5px solid #3cffaa; border-top:1px solid rgba(60,255,170,0.18); box-shadow:0 0 18px rgba(60,255,170,0.10);'>
                        <h4 style='color:#3cffaa; margin-top:0; letter-spacing:0.3px;'>🌲 Carbon Offset</h4>
                        <p style='font-size:26px; font-weight:700; margin-bottom:5px; color:#eaf6f1; text-shadow:0 0 12px rgba(60,255,170,0.35);'>{int(equivalent_trees)} Trees</p>
                        <p style='color:#8fa3ad; font-size:14px; margin-top:0;'>
                            Equivalent number of mature trees absorbing CO2 for a full year.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with imp_col2:
                st.markdown(
                    f"""
                    <div style='background:linear-gradient(135deg,#12191f 0%,#0b1116 100%); padding:20px; border-radius:14px; border-left:5px solid #00d4ff; border-top:1px solid rgba(0,212,255,0.18); box-shadow:0 0 18px rgba(0,212,255,0.10);'>
                        <h4 style='color:#00d4ff; margin-top:0; letter-spacing:0.3px;'>🚗 EV Driving Range</h4>
                        <p style='font-size:26px; font-weight:700; margin-bottom:5px; color:#eaf6f1; text-shadow:0 0 12px rgba(0,212,255,0.35);'>{ev_distance_km:,.1f} km</p>
                        <p style='color:#8fa3ad; font-size:14px; margin-top:0;'>
                            Distance an Electric Vehicle could travel using your generated energy.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with imp_col3:
                st.markdown(
                    f"""
                    <div style='background:linear-gradient(135deg,#12191f 0%,#0b1116 100%); padding:20px; border-radius:14px; border-left:5px solid #2fe0c0; border-top:1px solid rgba(47,224,192,0.18); box-shadow:0 0 18px rgba(47,224,192,0.10);'>
                        <h4 style='color:#2fe0c0; margin-top:0; letter-spacing:0.3px;'>💡 Household Power</h4>
                        <p style='font-size:26px; font-weight:700; margin-bottom:5px; color:#eaf6f1; text-shadow:0 0 12px rgba(47,224,192,0.30);'>{int(household_days)} Days</p>
                        <p style='color:#8fa3ad; font-size:14px; margin-top:0;'>
                            Number of days a standard household could be powered (10 kWh/day).
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with imp_col4:
                st.markdown(
                    f"""
                    <div style='background:linear-gradient(135deg,#12191f 0%,#0b1116 100%); padding:20px; border-radius:14px; border-left:5px solid #4d8cff; border-top:1px solid rgba(77,140,255,0.18); box-shadow:0 0 18px rgba(77,140,255,0.10);'>
                        <h4 style='color:#4d8cff; margin-top:0; letter-spacing:0.3px;'>⛽ Gasoline Driving Avoided</h4>
                        <p style='font-size:26px; font-weight:700; margin-bottom:5px; color:#eaf6f1; text-shadow:0 0 12px rgba(77,140,255,0.30);'>{gasoline_car_km:,.0f} km</p>
                        <p style='color:#8fa3ad; font-size:14px; margin-top:0;'>
                            Distance a gasoline car would drive to emit the same CO2 you avoided ({CAR_CO2_PER_KM_G:,.0f} g/km).
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            st.markdown("### 📈 Generation Trend")
            st.line_chart(plot_df.set_index("reading_date")["daily_yield"])

            with st.expander("🔎 View Raw Database Records"):
                st.dataframe(plot_df)
    
        else:
            st.info("No production data found yet. Upload a CSV file below to get started!")

        st.markdown("---")
        st.subheader("📥 Upload Inverter Report (CSV)")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

        if uploaded_file is not None:
            try:
                raw_df = pd.read_csv(uploaded_file)
                cleaned_df = clean_uploaded_csv(raw_df)

                st.write("### Preview of cleaned data (Converted to kWh)")
                st.dataframe(cleaned_df)

                removed_rows = len(raw_df) - len(cleaned_df)
                st.caption(
                    f"Original rows: {len(raw_df)} | "
                    f"Valid daily rows: {len(cleaned_df)} | "
                    f"Removed rows (like summary): {removed_rows}"
                )

                if removed_rows > 0:
                    st.info("Non-daily / summary / invalid row(s) were removed automatically.")

                if st.button("Save Data to GreenMine Database"):
                    success, msg = save_readings_to_db(cleaned_df, st.session_state["user_id"])
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            except Exception as e:
                st.error(f"Error: {e}")

# LOGIN
elif choice == "Login":
    st.subheader("Login to your Account")

    if not st.session_state.get("pending_verification", False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        st.markdown(
            f"**🔐 Security Check:** What is "
            f"`{st.session_state['captcha_a']} + {st.session_state['captcha_b']}` ?"
        )
        captcha_input = st.text_input("Your Answer", key="captcha_input")

        col_l1, col_l2 = st.columns([1, 1])

        with col_l2:
            if st.button("🔄 New Captcha"):
                generate_captcha()
                st.rerun()

        with col_l1:
            login_clicked = st.button("Login")

        if login_clicked:
            if captcha_input.strip() != str(st.session_state["captcha_answer"]):
                st.error("❌ Incorrect captcha answer. Please try again.")
                generate_captcha()
            else:
                user = login_user(username, password)

                if user:                                   # (20)
                    if user["email_verified"] == 1:        # (24)
                        st.session_state["logged_in"] = True
                        st.session_state["user_id"] = user["id"]
                        st.session_state["username"] = user["username"]
                        st.session_state["full_name"] = user["full_name"]
                        st.success(f"Welcome back, {user['full_name']}!")
                        st.rerun()
                    else:                                  # (24)
                        st.session_state["temp_user_id"] = user["id"]
                        st.session_state["temp_email"] = user["email"]
                        st.session_state["pending_verification"] = True

                        conn = get_db_connection()
                        try:
                            email_verification.create_verification_request(
                                conn,
                                user["id"],
                                user["email"]
                            )
                            status = email_verification.get_latest_verification_status(
                                conn,
                                user["id"]
                            )
                        finally:
                            conn.close()

                        if status and status["delivery_status"] == "sent":
                            st.session_state["otp_notice"] = {"ok": True, "msg": "A verification code was just sent to your email."}
                        else:
                            st.session_state["otp_notice"] = {"ok": False, "msg": "Could not send the code. Use 'Resend Code' below."}

                        st.rerun()

                else:                                      
                    st.error("Invalid Username or Password.")

    else:
        st.info("Please enter the verification code sent to your email.")

        notice = st.session_state.pop("otp_notice", None)
        if notice:
            if notice.get("ok"):
                st.success(notice.get("msg", "Verification code sent successfully."))
            else:
                st.error(notice.get("msg", "Failed to send verification code."))

        if not email_verification.is_email_sending_configured() and st.session_state.get("last_otp"):
            st.warning(
                f"SMTP is not configured yet. Temporary development OTP: {st.session_state['last_otp']}"
            )

        otp_input = st.text_input("6-Digit Code", max_chars=6)

        col_v1, col_v2, col_v3 = st.columns(3)

        with col_v1:
            if st.button("Verify Now"):
                code_clean = (otp_input or "").strip()

                if not code_clean:
                    st.error("Please enter the verification code.")
                    st.stop()

                if not (code_clean.isdigit() and len(code_clean) == 6):
                    st.error("The code must be exactly 6 digits.")
                    st.stop()

                else:
                    conn = get_db_connection()
                    try:
                        success, msg = email_verification.verify_code(
                            conn,
                            st.session_state["temp_user_id"],
                            code_clean
                        )

                        if success:
                            user = login_user_by_id(st.session_state["temp_user_id"])

                            if not user:
                                st.error("Account could not be loaded. Please log in again.")
                                st.session_state["pending_verification"] = False
                                st.session_state["temp_user_id"] = None
                                st.session_state["temp_email"] = ""
                                st.session_state.pop("last_otp", None)
                                st.rerun()

                            st.session_state["logged_in"] = True
                            st.session_state["user_id"] = user["id"]
                            st.session_state["username"] = user["username"]
                            st.session_state["full_name"] = user["full_name"]
                            st.session_state["pending_verification"] = False
                            st.session_state["temp_user_id"] = None
                            st.session_state["temp_email"] = ""
                            st.session_state["last_otp"] = ""

                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    finally:
                        conn.close()

        with col_v2:
            if st.button("Resend Code"):
                conn = get_db_connection()
                try:
                    code = email_verification.create_verification_request(
                        conn,
                        st.session_state["temp_user_id"],
                        st.session_state["temp_email"]
                    )

                    status = email_verification.get_latest_verification_status(
                        conn,
                        st.session_state["temp_user_id"]
                    )

                    if email_verification.is_email_sending_configured():
                        if status and status.get("email_sent"):
                            st.success("A new verification code was sent to your email.")
                        elif status and status.get("delivery_status") == "failed":
                            st.error(
                                "New code was created, but email delivery failed: "
                                f"{status.get('last_error')}"
                            )
                        else:
                            st.success("A new verification request was created.")
                    else:
                        st.session_state["last_otp"] = code
                        st.success(f"SMTP is not configured yet. Temporary OTP: {code}")

                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Failed to resend code: {e}")
                finally:
                    conn.close()

        with col_v3:
            if st.button("Back to Login"):
                st.session_state["pending_verification"] = False
                st.session_state["temp_user_id"] = None
                st.session_state["temp_email"] = ""
                st.session_state.pop("last_otp", None)      
                st.session_state.pop("otp_notice", None)
                st.rerun()

# REGISTER
elif choice == "Register":
    st.subheader("Create a New Account")

    new_name = st.text_input("Full Name")
    new_email = st.text_input("Email Address")
    new_user = st.text_input("Choose Username")
    new_password = st.text_input("Choose Password", type="password")

    if st.button("Sign Up"):
        if new_name and new_user and new_password and new_email:
            success, message = register_user(new_user, new_password, new_name, new_email)

            if success:
                st.success(message)
                placeholder = st.empty()
                for remaining in range(3, 0, -1):
                    placeholder.info(f"✅ Redirecting to Login in {remaining}...")
                    time.sleep(1)
                st.session_state["nav_override"] = "Login"
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Please fill in all fields.")

# DASHBOARD PAGE
elif choice == "Dashboard":
    st.title("📊 Forecast Dashboard")

    if not st.session_state["logged_in"]:
        st.warning("Please log in first.")
    else:
        plant = get_user_plant(st.session_state["user_id"])
        if plant is None:
            st.info("اول از صفحه Plant Info اطلاعات نیروگاهت رو ثبت کن.")
        elif not is_plant_info_complete(st.session_state["user_id"]):
            st.warning("اطلاعات نیروگاه ناقصه. برو صفحه Plant Info و کاملش کن.")
        else:
            render_dashboard(plant)

# PLANT INFO PAGE
elif choice == "Plant Info":
    st.title("🏭 Plant Technical Information")

    if not st.session_state["logged_in"]:
        st.warning("Please log in first.")
    else:
        plant = get_user_plant(st.session_state["user_id"])

        if plant is None:
            st.error("No plant found for this account. Contact support.")
        else:
            st.info("Complete all fields below to unlock the dashboard.")

            with st.form("plant_info_form"):
                c1, c2 = st.columns(2)
                with c1:
                    capacity_ac = st.number_input("AC Capacity (kW)", min_value=0.0, step=1.0)
                    utm_easting = st.number_input("X — UTM Easting (m)", min_value=0.0, step=1.0)
                    utm_zone = st.text_input("UTM Zone", placeholder="39S")
                    tilt = st.number_input("Tilt Angle (°)", 0.0, 90.0, 30.0, 1.0)
                    panel_type = st.selectbox("Panel Type", ["Monocrystalline", "Polycrystalline", "Thin-Film", "Bifacial"])
                with c2:
                    utm_northing = st.number_input("Y — UTM Northing (m)", min_value=0.0, step=1.0)
                    performance_ratio = st.number_input("Performance Ratio", 0.0, 1.0, 0.80, 0.01)
                    azimuth_label = st.selectbox("Azimuth (Direction)", list(AZIMUTH_DIRECTIONS.keys()), index=4)
                    mount_type = st.selectbox("Mount Type", ["Fixed", "Single-Axis Tracker", "Dual-Axis Tracker", "Rooftop"])

                submitted = st.form_submit_button("💾 Save Plant Information")

            if submitted:
                if capacity_ac <= 0 or not utm_zone.strip():
                    st.error("AC capacity and UTM zone are required.")
                elif utm_easting <= 0 or utm_northing <= 0:
                    st.error("UTM coordinates (X and Y) are required.")
                else:
                    azimuth = AZIMUTH_DIRECTIONS[azimuth_label]
                    conn = get_db_connection()
                    conn.execute("""
                        UPDATE plants SET
                            capacity_ac = ?,
                            utm_easting = ?, utm_northing = ?, utm_zone = ?,
                            tilt = ?, azimuth = ?, performance_ratio = ?,
                            panel_type = ?, mount_type = ?,
                            info_completed = 1
                        WHERE id = ?
                    """, (capacity_ac, utm_easting, utm_northing,
                          utm_zone.strip().upper(),
                          tilt, azimuth, performance_ratio,
                          panel_type, mount_type, plant["id"]))
                    conn.commit()
                    conn.close()
                    st.success("✅ Saved! Dashboard unlocked.")
                    st.rerun()

# LOGOUT
elif choice == "Logout":
    for key in ["logged_in", "user_id", "username", "email"]:
        st.session_state[key] = False if key == "logged_in" else None
    st.success("👋 Logged out successfully.")
    st.rerun()

# FOOTER
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: grey;'>GreenMine System v1.3 | 2026</p>",
    unsafe_allow_html=True,
)
