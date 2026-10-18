"""
Standalone i18n layer for GreenMine / Renewable Energy Dashboard.
No changes needed in existing modules except:
    import i18n
    i18n.init()                  # once, near session-state setup
    i18n.language_selector()     # once, in the sidebar
    i18n.t("key")                # wherever you want a translated string
"""

import streamlit as st

DEFAULT_LANG = "en"
LANG_KEY = "app_lang"
LANGUAGES = {
    "en": {"label": "English", "rtl": False},
    "fa": {"label": "فارسی", "rtl": True},
}

#translations
TEXTS = {
    #navigation / general
    "nav.menu":            {"en": "Navigation Menu",       "fa": "منوی ناوبری"},
    "nav.home":            {"en": "Home",                  "fa": "خانه"},
    "nav.login":           {"en": "Login",                 "fa": "ورود"},
    "nav.register":        {"en": "Register",              "fa": "ثبت‌نام"},
    "nav.plant_info":      {"en": "Plant Info",            "fa": "اطلاعات نیروگاه"},
    "nav.dashboard":       {"en": "📊 Forecast Dashboard",  "fa": "📊 داشبورد پیش‌بینی"},
    "nav.logout":          {"en": "Logout",                "fa": "خروج"},
    "nav.language":        {"en": "Language",              "fa": "زبان"},
    "nav.incomplete_info": {"en": "⚠️ Please complete your plant information first.",
                            "fa": "⚠️ لطفاً ابتدا اطلاعات نیروگاه را کامل کنید."},

    #page titles
    "page.welcome":     {"en": "Welcome to GreenMine",              "fa": "به گرین‌ماین خوش آمدید"},
    "page.token_demo": {"en": "🌿 Carbon Token (VCT) — Demo",       "fa": "🌿 توکن کربن (VCT) — نمونه"},
    "page.upload_csv":  {"en": "📥 Upload Inverter Report (CSV)",   "fa": "📥 بارگذاری گزارش اینورتر (CSV)"},
    "page.login":       {"en": "Login to your Account",             "fa": "ورود به حساب کاربری"},
    "page.register":    {"en": "Create a New Account",              "fa": "ساخت حساب کاربری جدید"},
    "page.plant_tech":  {"en": "🏭 Plant Technical Information",    "fa": "🏭 اطلاعات فنی نیروگاه"},

    #plant specs
    "spec.header":       {"en": "Plant Specifications", "fa": "مشخصات نیروگاه"},
    "spec.ac_capacity":  {"en": "AC Capacity",          "fa": "ظرفیت AC"},
    "spec.tilt":         {"en": "Tilt",                 "fa": "زاویه شیب"},
    "spec.azimuth":      {"en": "Azimuth",              "fa": "آزیموت (جهت)"},
    "spec.pr":           {"en": "Performance Ratio",    "fa": "نسبت عملکرد"},
    "spec.panel_type":   {"en": "Panel Type",           "fa": "نوع پنل"},
    "spec.mount_type":   {"en": "Mount Type",           "fa": "نوع نصب"},
    "spec.location":     {"en": "Location",             "fa": "موقعیت"},
    "spec.utm_error":    {"en": "Could not convert UTM coordinates.",
                          "fa": "تبدیل مختصات UTM ممکن نشد."},

    #specs & location
    "spec.location_full": {"en": "Location: {lat}, {lon} | UTM zone {zone}",
                           "fa": "موقعیت: {lat}, {lon} | زون UTM {zone}"},

    #forecast meta
    "fc.today":           {"en": "Today", "fa": "امروز"},
    "fc.horizon":         {"en": "Forecast horizon", "fa": "افق پیش‌بینی"},
    "fc.horizon_desc":    {"en": "{api} days from weather service + {clim} days from climate model",
                           "fa": "{api} روز از سرویس آب‌وهوا + {clim} روز از مدل اقلیمی"},
    "fc.next_month_note": {"en": "The selected month is outside the 15-day weather service window; "
                                 "the whole calculation is based on the climate model.",
                           "fa": "ماه انتخابی خارج از پنجره ۱۵ روزه سرویس آب‌وهواست؛ "
                                 "کل محاسبه بر مدل اقلیمی است."},
    "fc.day_of":          {"en": "Day of {month}", "fa": "روز {month}"},
    "fc.production":      {"en": "Production (kWh)", "fa": "تولید (کیلووات‌ساعت)"},
    "fc.source":          {"en": "Data source", "fa": "منبع داده"},
    "fc.src_api":         {"en": "API forecast", "fa": "پیش‌بینی API"},
    "fc.src_climate":     {"en": "Climate model", "fa": "مدل اقلیمی"},
    "fc.api_days_note":   {"en": "{n} days from the API in this window.",
                           "fa": "{n} روز از API در این پنجره."},
    "fc.persian":          {"en": "persian date", "fa": "تاریخ شمسی"},
    "fc.gregorian":       {"en": "Gregorian date", "fa": "تاریخ میلادی"},
    "fc.ghi":             {"en": "GHI (kWh/m²/day)", "fa": "تابش کل افقی (kWh/m²/روز)"},
    "fc.geometry_factor": {"en": "Geometry factor", "fa": "ضریب هندسی"},
    "fc.mount_factor":    {"en": "Mount factor", "fa": "ضریب نصب"},
    "fc.panel_factor":    {"en": "Panel factor", "fa": "ضریب پنل"},

    #table
    "tbl.header":         {"en": "Daily breakdown", "fa": "جزئیات روزانه"},
    "tbl.day":            {"en": "Day", "fa": "روز"},
    "tbl.segment":        {"en": "Segment", "fa": "بازه"},

    #revenue
    "rev.tariff":         {"en": "Guaranteed purchase tariff (IRR per kWh)",
                           "fa": "تعرفه خرید تضمینی (ریال بر کیلووات‌ساعت)"},
    "rev.month_total":    {"en": "{month} revenue", "fa": "درآمد {month}"},
    "rev.avg_daily":      {"en": "Average daily revenue", "fa": "میانگین درآمد روزانه"},

    #environment
    "env.tokens":         {"en": "Carbon tokens", "fa": "توکن کربن"},
    "env.tokens_help":    {"en": "One token per {kg} kg of CO₂ avoided.",
                           "fa": "هر توکن معادل {kg} کیلوگرم CO₂ اجتناب‌شده."},
    "env.co2_help":       {"en": "Grid emission factor: {factor} kg per kWh.",
                           "fa": "ضریب انتشار شبکه: {factor} کیلوگرم بر کیلووات‌ساعت."},
    "env.trees_help":     {"en": "A mature tree absorbs {kg} kg of CO₂ per year.",
                           "fa": "یک درخت بالغ سالانه {kg} کیلوگرم CO₂ جذب می‌کند."},
    "env.car_range":      {"en": "Electric car range", "fa": "مسافت خودروی برقی"},
    "env.car_help":       {"en": "Assuming {kwh} kWh per km.",
                           "fa": "با فرض {kwh} کیلووات‌ساعت بر کیلومتر."},
    "env.gasoline":       {"en": "Gasoline driving avoided", "fa": "رانندگی بنزینی اجتناب‌شده"},
    "env.gasoline_help":  {"en": "An average car emits {g} g of CO₂ per km.",
                           "fa": "خودروی متوسط {g} گرم CO₂ بر کیلومتر منتشر می‌کند."},
    "env.homes":          {"en": "Homes powered", "fa": "خانه‌های تأمین‌شده"},
    "env.homes_help":     {"en": "A typical household uses {kwh} kWh per month.",
                           "fa": "مصرف خانوار معمول {kwh} کیلووات‌ساعت در ماه."},

    #units
    "unit.km":            {"en": "km", "fa": "کیلومتر"},
    "unit.kg":            {"en": "kg", "fa": "کیلوگرم"},
    "unit.irr":           {"en": "IRR", "fa": "ریال"},

    #forecast
    "fc.fetching":     {"en": "Fetching irradiance data...", "fa": "در حال دریافت داده تابش..."},
    "fc.nasa_down":    {"en": "NASA POWER data is unavailable right now. Try again later.",
                        "fa": "داده NASA POWER در دسترس نیست. کمی بعد دوباره تلاش کنید."},
    "fc.title":        {"en": "Production Forecast — {month}",
                        "fa": "پیش‌بینی تولید — {month}"},
    "fc.days_1_15":    {"en": "Days 1-15",   "fa": "روزهای ۱ تا ۱۵"},
    "fc.days_16_plus": {"en": "Days 16+",    "fa": "روزهای ۱۶ به بعد"},
    "fc.total":        {"en": "Total",       "fa": "مجموع"},
    "fc.api_window":   {"en": "API forecast", "fa": "پیش‌بینی API"},
    "fc.climate":      {"en": "Climate model", "fa": "مدل اقلیمی"},
    "fc.no_api_data":  {"en": "No API forecast data for this window.",
                        "fa": "داده پیش‌بینی API برای این بازه موجود نیست."},
    "fc.avg_daily":    {"en": "Average daily output", "fa": "میانگین تولید روزانه"},
    "fc.peak_day":     {"en": "Peak day",             "fa": "روز اوج تولید"},

    #revenue & environment
    "rev.header":      {"en": "Revenue Estimate", "fa": "برآورد درآمد"},
    "env.header":      {"en": "Environmental Impact for {month}",
                        "fa": "اثرات زیست‌محیطی برای {month}"},
    "env.basis":  {"en": "Based on {kwh} kWh forecast for {month}.",
               "fa": "بر پایهٔ پیش‌بینی {kwh} کیلووات‌ساعت برای {month}."},
    "env.co2":         {"en": "CO₂ avoided",   "fa": "کربن جلوگیری‌شده"},
    "env.trees":       {"en": "Equivalent trees", "fa": "معادل درخت"},
    "env.caption":     {"en": "Based on the selected month's forecast.",
                        "fa": "بر پایه پیش‌بینی ماه انتخاب‌شده."},

    #units
    "unit.kwh":  {"en": "kWh", "fa": "کیلووات‌ساعت"},
    "unit.mwh":  {"en": "MWh", "fa": "مگاوات‌ساعت"},
    "unit.kw":   {"en": "kW",  "fa": "کیلووات"},
    "unit.days": {"en": "days", "fa": "روز"},
    "unit.ton":  {"en": "t",   "fa": "تن"},

}

#persian month names
PERSIAN_MONTHS = {
    "en": ["Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
           "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"],
    "fa": ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
           "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"],
}

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


#core API
def init(default=DEFAULT_LANG):
    """Register the language key in session_state. Safe to call repeatedly."""
    if LANG_KEY not in st.session_state:
        st.session_state[LANG_KEY] = default


def get_lang():
    init()
    return st.session_state[LANG_KEY]


def set_lang(code):
    if code in LANGUAGES:
        st.session_state[LANG_KEY] = code


def is_rtl():
    return LANGUAGES[get_lang()]["rtl"]


def t(key, **kwargs):
    """Translate a key. Falls back to English, then to the key itself."""
    entry = TEXTS.get(key)
    if entry is None:
        return key
    lang = get_lang()
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def month_name(index_1_based):
    """persian month name in the active language. index: 1..12"""
    names = PERSIAN_MONTHS[get_lang()]
    i = int(index_1_based) - 1
    return names[i] if 0 <= i < 12 else str(index_1_based)


def localize_month(english_name):
    """Map an English persian month name coming from prediction_engine to the active language."""
    try:
        idx = PERSIAN_MONTHS["en"].index(english_name)
    except ValueError:
        return english_name
    return PERSIAN_MONTHS[get_lang()][idx]


def num(value, digits=None):
    """Format a number, using Persian digits when the UI is Persian."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        s = str(value)
        return s.translate(_PERSIAN_DIGITS) if get_lang() == "fa" else s

    if digits is not None:
        s = f"{value:,.{digits}f}"
    elif value.is_integer():
        s = f"{int(value):,}"
    else:
        s = f"{value:,.2f}"
    return s.translate(_PERSIAN_DIGITS) if get_lang() == "fa" else s

#UI helpers
def language_selector(location="sidebar"):
    """Drop-in language picker. Uses its own widget key to avoid collisions."""
    init()
    container = st.sidebar if location == "sidebar" else st
    codes = list(LANGUAGES.keys())
    current = get_lang()
    selected = container.selectbox(
        t("nav.language"),
        codes,
        index=codes.index(current),
        format_func=lambda c: LANGUAGES[c]["label"],
        key="i18n_lang_selector",
    )
    if selected != current:
        set_lang(selected)
        st.rerun()
    return get_lang()


def apply_direction():
    """Inject RTL styling only when needed. Call right after set_page_config."""
    if not is_rtl():
        return
    st.markdown(
        """
        <style>
        .stApp, section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stMetricDelta"] { direction: ltr; }
        .stApp code, .stApp pre { direction: ltr; text-align: left; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def nav_labels():
    """Map internal page names -> translated labels for selectbox format_func."""
    return {
        "Home": t("nav.home"),
        "Login": t("nav.login"),
        "Register": t("nav.register"),
        "Plant Info": t("nav.plant_info"),
        "Dashboard": t("nav.dashboard"),
        "Logout": t("nav.logout"),
    }
