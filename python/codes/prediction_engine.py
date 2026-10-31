"""
موتور محاسبات پیش‌بینی تولید نیروگاه خورشیدی — GreenMine
- تبدیل UTM به طول/عرض جغرافیایی (بدون نیاز به pyproj)
- دریافت تابش ماهانه از NASA POWER
- تبدیل به تقویم شمسی و محاسبه تولید/درآمد/اثر زیست‌محیطی
"""
import math
import requests

# ثابت‌های محاسباتی
GRID_EMISSION_FACTOR = 0.66      # kg CO2 / kWh  (هم‌راستا با proj1.py)
CAR_CO2_PER_KM_G = 148.0         # gram CO2 / km — خودروی بنزینی
CARBON_TOKEN_UNIT_KG = 10.0      # 1 VCT = 10 kg CO2 اجتناب‌شده
CARBON_TOKEN_SYMBOL = "VCT"      # Verified Carbon Token (demo, off-chain)
EV_CONSUMPTION_KWH_PER_KM = 0.18 # مصرف خودروی برقی
TREE_CO2_KG_PER_YEAR = 21.0      # جذب سالانه یک درخت بالغ
HOME_KWH_PER_MONTH = 300.0       # مصرف ماهانه یک خانه

# ضریب نوع نصب
MOUNT_FACTORS = {
    "Fixed": 1.00,
    "Single-Axis Tracker": 1.25,
    "Dual-Axis Tracker": 1.35,
    "Rooftop": 0.97,
}

# ضریب نوع پنل
PANEL_FACTORS = {
    "Monocrystalline": 1.00,
    "Polycrystalline": 0.95,
    "Thin-Film": 0.88,
    "Bifacial": 1.08,
}

# ماه‌های شمسی و تعداد روز
JALALI_MONTHS = [
    ("فروردین", 31), ("اردیبهشت", 31), ("خرداد", 31),
    ("تیر", 31), ("مرداد", 31), ("شهریور", 31),
    ("مهر", 30), ("آبان", 30), ("آذر", 30),
    ("دی", 30), ("بهمن", 30), ("اسفند", 29),
]

# تبدیل ماه میلادی به شمسی
JALALI_TO_GREGORIAN_WEIGHTS = {
    "فروردین":  {"MAR": 0.35, "APR": 0.65},
    "اردیبهشت": {"APR": 0.32, "MAY": 0.68},
    "خرداد":    {"MAY": 0.32, "JUN": 0.68},
    "تیر":      {"JUN": 0.29, "JUL": 0.71},
    "مرداد":    {"JUL": 0.29, "AUG": 0.71},
    "شهریور":   {"AUG": 0.29, "SEP": 0.71},
    "مهر":      {"SEP": 0.27, "OCT": 0.73},
    "آبان":     {"OCT": 0.30, "NOV": 0.70},
    "آذر":      {"NOV": 0.30, "DEC": 0.70},
    "دی":       {"DEC": 0.33, "JAN": 0.67},
    "بهمن":     {"JAN": 0.35, "FEB": 0.65},
    "اسفند":    {"FEB": 0.31, "MAR": 0.69},
}

# ۱) تبدیل UTM → Lat/Lon
def _parse_zone(utm_zone):
    """'39S' → (39, 'N')  — حرف C..M جنوبی، N..X شمالی."""
    if not utm_zone:
        raise ValueError("UTM zone خالی است.")
    z = str(utm_zone).strip().upper()
    digits = "".join(ch for ch in z if ch.isdigit())
    letters = "".join(ch for ch in z if ch.isalpha())
    if not digits:
        raise ValueError(f"شماره zone در '{utm_zone}' پیدا نشد.")
    number = int(digits)
    if not 1 <= number <= 60:
        raise ValueError(f"شماره zone نامعتبر: {number}")
    hemisphere = "N"
    if letters:
        letter = letters[0]
        hemisphere = "S" if letter < "N" else "N"
    return number, hemisphere


def utm_to_latlon(easting, northing, utm_zone):
    """تبدیل مختصات UTM به (latitude, longitude) روی بیضوی WGS84."""
    zone, hemisphere = _parse_zone(utm_zone)

    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0 = 0.9996

    x = float(easting) - 500000.0
    y = float(northing)
    if hemisphere == "S":
        y -= 10000000.0

    M = y / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))

    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
        + (1097 * e1**4 / 512) * math.sin(8 * mu)
    )

    sin_phi1 = math.sin(phi1)
    cos_phi1 = math.cos(phi1)
    tan_phi1 = math.tan(phi1)

    C1 = ep2 * cos_phi1**2
    T1 = tan_phi1**2
    N1 = a / math.sqrt(1 - e2 * sin_phi1**2)
    R1 = a * (1 - e2) / (1 - e2 * sin_phi1**2) ** 1.5
    D = x / (N1 * k0)

    lat = phi1 - (N1 * tan_phi1 / R1) * (
        D**2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * ep2) * D**4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * ep2 - 3 * C1**2) * D**6 / 720
    )

    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    lon = lon0 + (
        D
        - (1 + 2 * T1 + C1) * D**3 / 6
        + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * ep2 + 24 * T1**2) * D**5 / 120
    ) / cos_phi1

    return math.degrees(lat), math.degrees(lon)

# ۲) دریافت تابش از NASA POWER
NASA_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"

def fetch_nasa_irradiance(lat, lon, timeout=25):
    """
    میانگین بلندمدت تابش افقی روزانه (kWh/m²/day) برای هر ماه میلادی.
    خروجی: dict مثل {'JAN': 3.1, ..., 'DEC': 3.0}
    """
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "format": "JSON",
    }
    resp = requests.get(NASA_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    raw = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    result = {}
    for m in months:
        value = raw.get(m)
        if value is None or value < 0:
            raise ValueError(f"داده NASA برای ماه {m} نامعتبر است.")
        result[m] = float(value)
    return result

# ۳) ضریب زاویه پنل
def tilt_azimuth_factor(tilt, azimuth, latitude):
    """
    ضریب تقریبی افزایش/کاهش تابش روی سطح شیب‌دار نسبت به سطح افقی.
    مدل ساده‌شده و مهندسی — برای دمو کافی است، نه برای طراحی نهایی.
    """
    lat_abs = abs(latitude)
    optimal_tilt = min(lat_abs * 0.9, 40.0)

    # سود شیب: در زاویه بهینه بیشترین مقدار
    tilt_gain = 1.0 + 0.18 * math.cos(math.radians(tilt - optimal_tilt))
    tilt_gain -= 0.18
    tilt_gain += 0.18 * math.cos(math.radians(optimal_tilt)) * 0.0  

    base = 1.0 + 0.20 * (
        math.cos(math.radians(tilt - optimal_tilt)) - math.cos(math.radians(optimal_tilt))
    )

    # جریمه انحراف از جنوب (نیم‌کره شمالی)
    target_azimuth = 180.0 if latitude >= 0 else 0.0
    deviation = abs(azimuth - target_azimuth)
    deviation = min(deviation, 360 - deviation)
    azimuth_penalty = 1.0 - 0.0022 * deviation * (tilt / 30.0)
    azimuth_penalty = max(azimuth_penalty, 0.55)

    return max(base * azimuth_penalty, 0.40)

# ۴) تولید ماهانه
def monthly_production(plant, irradiance=None):
    """
    plant: sqlite3.Row یا dict با کلیدهای قرارداد proj1.py
    خروجی: list of dict شامل ماه شمسی، روزها، تابش، تولید (kWh)
    """
    capacity_ac = float(plant["capacity_ac"])
    pr = float(plant["performance_ratio"])
    tilt = float(plant["tilt"])
    azimuth = float(plant["azimuth"])

    lat, lon = utm_to_latlon(
        plant["utm_easting"], plant["utm_northing"], plant["utm_zone"]
    )

    if irradiance is None:
        irradiance = fetch_nasa_irradiance(lat, lon)

    geo_factor = tilt_azimuth_factor(tilt, azimuth, lat)
    mount_factor = MOUNT_FACTORS.get(plant["mount_type"], 1.0)
    panel_factor = PANEL_FACTORS.get(plant["panel_type"], 1.0)

    rows = []
    for name, days in JALALI_MONTHS:
        weights = JALALI_TO_GREGORIAN_WEIGHTS[name]
        ghi = sum(irradiance[g] * w for g, w in weights.items())

        # kWh = kWp × (kWh/m²/day) × days × ضرایب
        energy = ghi * days * capacity_ac * pr * geo_factor * mount_factor * panel_factor

        rows.append({
            "ماه": name,
            "روز": days,
            "تابش (kWh/m²/day)": round(ghi, 2),
            "تولید (kWh)": round(energy, 1),
        })

    return {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "geo_factor": round(geo_factor, 3),
        "mount_factor": mount_factor,
        "panel_factor": panel_factor,
        "months": rows,
        "annual_kwh": round(sum(r["تولید (kWh)"] for r in rows), 1),
    }

# ۵) درآمد و اثر زیست‌محیطی
def revenue(energy_kwh, price_per_kwh):
    """درآمد پیش‌بینی‌شده بر اساس نرخ خرید تضمینی برق."""
    return energy_kwh * float(price_per_kwh)

def environmental_impact(energy_kwh, emission_factor=GRID_EMISSION_FACTOR):
    """معادل‌های زیست‌محیطی تولید انرژی + توکن کربن دمو."""
    co2_kg = energy_kwh * emission_factor
    return {
        "carbon_saved_kg":  round(co2_kg, 1),
        "carbon_saved_ton": round(co2_kg / 1000, 3),
        "carbon_tokens":    round(co2_kg / CARBON_TOKEN_UNIT_KG, 2),
        "token_symbol":     CARBON_TOKEN_SYMBOL,
        "ev_km":            round(energy_kwh / EV_CONSUMPTION_KWH_PER_KM, 0),
        "gasoline_car_km":  round(co2_kg * 1000 / CAR_CO2_PER_KM_G, 0),
        "trees_equivalent": round(co2_kg / TREE_CO2_KG_PER_YEAR, 1),
        "homes_powered":    round(energy_kwh / HOME_KWH_PER_MONTH, 1),
    }

# تقویم شمسی و پیش بینی ماه بعد
import calendar
from datetime import date, timedelta

JALALI_MONTHS_EN = [
    "Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
    "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand",
]

NASA_MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                   "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_HORIZON_DAYS = 15

# تبدیل تقویم
def gregorian_to_jalali(gy, gm, gd):
    g_dm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy, gy = 979, gy - 1600
    else:
        jy, gy = 0, gy - 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) \
        + ((gy2 + 399) // 400) - 80 + gd + g_dm[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy, jm, jd):
    if jy > 979:
        gy, jy = 1600, jy - 979
    else:
        gy = 621
    days = (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + 78 + jd
    days += (jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    month_len = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > month_len[gm]:
        gd -= month_len[gm]
        gm += 1
    return gy, gm, gd


def is_jalali_leap(jy):
    """Esfand 30 exists only in a leap Jalali year."""
    gy, gm, gd = jalali_to_gregorian(jy, 12, 30)
    return gregorian_to_jalali(gy, gm, gd) == (jy, 12, 30)


def jalali_month_days(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def current_jalali_date(today=None):
    today = today or date.today()
    return gregorian_to_jalali(today.year, today.month, today.day)


def next_jalali_month(jy, jm):
    return (jy, jm + 1) if jm < 12 else (jy + 1, 1)


def jalali_month_name(jm):
    return JALALI_MONTHS_EN[jm - 1]


# بخش اول پیش بینی 
def fetch_openmeteo_daily(lat, lon, start_date, end_date, timeout=20):
    """Daily GHI in kWh/m2/day, keyed by date. Empty dict on failure."""
    if start_date > end_date:
        return {}
    params = {
        "latitude": round(float(lat), 4),
        "longitude": round(float(lon), 4),
        "daily": "shortwave_radiation_sum",
        "timezone": "auto",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        daily = resp.json().get("daily", {}) or {}
        times = daily.get("time") or []
        values = daily.get("shortwave_radiation_sum") or []
    except Exception:
        return {}

    out = {}
    for t, v in zip(times, values):
        if v is None:
            continue
        try:
            out[date.fromisoformat(t)] = float(v) / 3.6   # MJ/m2 -> kWh/m2
        except Exception:
            continue
    return out


# پشتیبان اقلیم‌شناسی
def _greg_month_days(year, month):
    return calendar.monthrange(year, month)[1]


def climatology_ghi(irradiance, day):
    """Climatological GHI for a date, linearly interpolated between monthly means."""
    if not irradiance:
        return 0.0
    values = [v for v in irradiance.values() if isinstance(v, (int, float))]
    fallback = sum(values) / len(values) if values else 0.0
    cur = irradiance.get(NASA_MONTH_KEYS[day.month - 1], fallback)

    dim = _greg_month_days(day.year, day.month)
    mid = (dim + 1) / 2.0

    if day.day >= mid:
        nxt_m = day.month % 12 + 1
        nxt_y = day.year + (1 if day.month == 12 else 0)
        nxt = irradiance.get(NASA_MONTH_KEYS[nxt_m - 1], cur)
        span = (dim - mid) + (_greg_month_days(nxt_y, nxt_m) + 1) / 2.0
        w = 0.0 if span <= 0 else (day.day - mid) / span
        return cur + (nxt - cur) * min(max(w, 0.0), 1.0)

    prv_m = 12 if day.month == 1 else day.month - 1
    prv_y = day.year - (1 if day.month == 1 else 0)
    prv = irradiance.get(NASA_MONTH_KEYS[prv_m - 1], cur)
    p_dim = _greg_month_days(prv_y, prv_m)
    span = (p_dim - (p_dim + 1) / 2.0) + mid
    w = 0.0 if span <= 0 else (mid - day.day) / span
    return cur + (prv - cur) * min(max(w, 0.0), 1.0)


def _geo_factor(tilt, azimuth, lat):
    """Tolerant wrapper: works whether tilt_azimuth_factor takes lat or not."""
    try:
        return tilt_azimuth_factor(tilt, azimuth, lat)
    except TypeError:
        return tilt_azimuth_factor(tilt, azimuth)


# main entry point
def next_month_forecast(plant, today=None, irradiance=None,
                        daily_api=None, api_days=FORECAST_HORIZON_DAYS):
    """
    Forecast production for the NEXT Jalali month.
    Days 1-15  -> Open-Meteo daily forecast when the date is inside the horizon.
    Days 16-end -> NASA POWER climatology (interpolated).
    """
    today = today or date.today()
    cur_jy, cur_jm, cur_jd = gregorian_to_jalali(today.year, today.month, today.day)
    n_jy, n_jm = next_jalali_month(cur_jy, cur_jm)
    n_days = jalali_month_days(n_jy, n_jm)

    lat, lon = utm_to_latlon(plant["utm_easting"], plant["utm_northing"], plant["utm_zone"])
    if irradiance is None:
        irradiance = fetch_nasa_irradiance(lat, lon)

    capacity_ac = float(plant["capacity_ac"])
    pr = float(plant["performance_ratio"])
    geo = _geo_factor(float(plant["tilt"]), float(plant["azimuth"]), lat)
    mount = MOUNT_FACTORS.get(plant["mount_type"], 1.0)
    panel = PANEL_FACTORS.get(plant["panel_type"], 1.0)
    k = capacity_ac * pr * geo * mount * panel

    start_g = date(*jalali_to_gregorian(n_jy, n_jm, 1))
    end_g = start_g + timedelta(days=n_days - 1)
    horizon_end = today + timedelta(days=api_days)

    if daily_api is None:
        daily_api = fetch_openmeteo_daily(
            lat, lon, max(start_g, today), min(end_g, horizon_end)
        )

    rows, api_count = [], 0
    for d in range(1, n_days + 1):
        g = start_g + timedelta(days=d - 1)
        first_half = d <= 15
        api_val = daily_api.get(g) if first_half else None

        if api_val is not None:
            ghi, source = api_val, "API forecast"
            api_count += 1
        else:
            ghi, source = climatology_ghi(irradiance, g), "Climate model"

        rows.append({
            "day": d,
            "jalali_date": f"{n_jy:04d}/{n_jm:02d}/{d:02d}",
            "gregorian_date": g.isoformat(),
            "half": "Days 1-15" if first_half else "Days 16+",
            "ghi": round(ghi, 2),
            "production_kwh": round(ghi * k, 1),
            "source": source,
        })

    first_half_kwh = sum(r["production_kwh"] for r in rows if r["day"] <= 15)
    second_half_kwh = sum(r["production_kwh"] for r in rows if r["day"] > 15)

    return {
        "today_jalali": f"{cur_jy:04d}/{cur_jm:02d}/{cur_jd:02d}",
        "current_month_name": jalali_month_name(cur_jm),
        "current_year": cur_jy,
        "target_year": n_jy,
        "target_month": n_jm,
        "target_month_name": jalali_month_name(n_jm),
        "days_in_month": n_days,
        "days": rows,
        "first_half_kwh": first_half_kwh,
        "second_half_kwh": second_half_kwh,
        "total_kwh": first_half_kwh + second_half_kwh,
        "api_days": api_count,
        "model_days": n_days - api_count,
        "lat": lat,
        "lon": lon,
        "geo_factor": round(geo, 3),
        "mount_factor": mount,
        "panel_factor": panel,
        "irradiance": irradiance,
    }
