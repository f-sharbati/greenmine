from datetime import date
import altair as alt
import pandas as pd
import streamlit as st
import prediction_engine as pe
import i18n

CARD_CSS = """
<style>
.gm-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 16px;
    margin: 12px 0 22px 0;
}
.gm-card {
    background: linear-gradient(160deg, #12191f 0%, #0b1116 100%);
    border: 1px solid rgba(60, 255, 170, 0.18);
    border-radius: 20px;
    padding: 20px 18px;
    color: #e6eef2;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.45),
                inset 0 1px 0 rgba(255, 255, 255, 0.04);
    transition: transform .18s ease, border-color .18s ease;
}
.gm-card:hover {
    transform: translateY(-3px);
    border-color: rgba(60, 255, 170, 0.45);
}
.gm-icon {
    font-size: 22px;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    background: rgba(60, 255, 170, 0.10);
    border: 1px solid rgba(60, 255, 170, 0.22);
    margin-bottom: 12px;
}
.gm-value {
    font-size: 26px;
    font-weight: 700;
    color: #3cffaa;
    letter-spacing: -0.5px;
    text-shadow: 0 0 18px rgba(60, 255, 170, 0.35);
}
.gm-label {
    font-size: 13px;
    color: #a0b0ba;
    margin-top: 4px;
    font-weight: 500;
}
.gm-note {
    font-size: 11px;
    color: #6a7a85;
    margin-top: 6px;
}
div[data-testid="stMetric"] {
    background: linear-gradient(160deg, #12191f 0%, #0b1116 100%);
    border: 1px solid rgba(0, 212, 255, 0.16);
    border-radius: 18px;
    padding: 16px 18px;
}
div[data-testid="stMetricLabel"] p {
    color: #a0b0ba !important;
    font-size: 13px !important;
}
div[data-testid="stMetricValue"] {
    color: #00d4ff !important;
    font-weight: 700;
}
div[data-testid="stExpander"] {
    background: rgba(18, 25, 31, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
}
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
}
.stButton > button {
    background: linear-gradient(135deg, #16202a 0%, #12191f 100%);
    color: #3cffaa;
    border-radius: 12px;
    font-weight: 600;
}
.stButton > button:hover {
    border-color: #3cffaa;
    box-shadow: 0 0 16px rgba(60, 255, 170, 0.25);
}
h2, h3 {
    color: #e6eef2 !important;
    letter-spacing: -0.3px;
}
</style>
"""

def _cards(items):
    html = ['<div class="gm-grid">']
    for icon, value, label, note in items:
        html.append(
            '<div class="gm-card">'
            f'<div class="gm-icon">{icon}</div>'
            f'<div class="gm-value">{value}</div>'
            f'<div class="gm-label">{label}</div>'
            f'<div class="gm-note">{note}</div>'
            "</div>"
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

@st.cache_data(ttl=86400, show_spinner=False)
def _cached_irradiance(lat, lon):
    return pe.fetch_nasa_irradiance(lat, lon)

@st.cache_data(ttl=21600, show_spinner=False)
def _cached_daily(lat, lon, start_iso, end_iso):
    return pe.fetch_openmeteo_daily(
        lat, lon, date.fromisoformat(start_iso), date.fromisoformat(end_iso)
    )

def render_dashboard(plant):
    st.markdown(CARD_CSS, unsafe_allow_html=True)
    #plant specs
    st.subheader(i18n.t("spec.header"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(i18n.t("spec.ac_capacity"),
              f"{i18n.num(plant['capacity_ac'], 1)} {i18n.t('unit.kw')}")
    c2.metric(i18n.t("spec.tilt"),
              f"{i18n.num(plant['tilt'], 0)}°")
    c3.metric(i18n.t("spec.azimuth"),
              f"{i18n.num(plant['azimuth'], 0)}°")
    c4.metric(i18n.t("spec.pr"),
              i18n.num(plant["performance_ratio"], 2))

    #location
    try:
        lat, lon = pe.utm_to_latlon(
            plant["utm_easting"], plant["utm_northing"], plant["utm_zone"]
        )
    except Exception as exc:
        st.error(i18n.t("spec.utm_error", exc=exc))
        return

    st.caption(i18n.t(
        "spec.location_full",
        lat=i18n.num(lat, 4),
        lon=i18n.num(lon, 4),
        zone=i18n.num(plant["utm_zone"]),
        panel=plant["panel_type"],
        mount=plant["mount_type"],
    ))

    #data
    today = date.today()
    cur_jy, cur_jm, cur_jd = pe.current_jalali_date(today)
    n_jy, n_jm = pe.next_jalali_month(cur_jy, cur_jm)
    n_days = pe.jalali_month_days(n_jy, n_jm)

    start_g = date(*pe.jalali_to_gregorian(n_jy, n_jm, 1))
    end_g = date(*pe.jalali_to_gregorian(n_jy, n_jm, min(15, n_days)))
    api_start = max(start_g, today)
    api_end = min(end_g, today.fromordinal(today.toordinal() + pe.FORECAST_HORIZON_DAYS))

    with st.spinner(i18n.t("fc.fetching")):
        irradiance = _cached_irradiance(round(lat, 3), round(lon, 3))
        daily_api = (
            _cached_daily(round(lat, 3), round(lon, 3),
                          api_start.isoformat(), api_end.isoformat())
            if api_start <= api_end else {}
        )

    if not irradiance:
        st.error(i18n.t("fc.nasa_down"))
        return

    result = pe.next_month_forecast(
        plant, today=today, irradiance=irradiance, daily_api=daily_api
    )
    df = pd.DataFrame(result["days"])
    month_label = f"{result['target_month_name']} {result['target_year']}"

    #header
    st.divider()
    st.subheader(i18n.t("fc.header", month=month_label))
    st.caption(
        i18n.t("fc.today",
               date=f"{result['current_month_name']} {result['today_jalali']}") + " • " +
        i18n.t("fc.horizon", days=i18n.num(result["days_in_month"], 0)) + " • " +
        i18n.t("fc.split",
               api=i18n.num(result["api_days"], 0),
               model=i18n.num(result["model_days"], 0))
    )

    m1, m2, m3 = st.columns(3)
    m1.metric(i18n.t("fc.api_window"),
              f"{i18n.num(result['first_half_kwh'], 1)} {i18n.t('unit.kwh')}")
    m2.metric(i18n.t("fc.model_window"),
              f"{i18n.num(result['second_half_kwh'], 1)} {i18n.t('unit.kwh')}")
    m3.metric(i18n.t("fc.total", month=result["target_month_name"]),
              f"{i18n.num(result['total_kwh'], 1)} {i18n.t('unit.kwh')}")

    if result["api_days"] == 0:
        st.info(i18n.t("fc.next_month_note"))

    #daily chart
    df_first = df[df["day"] <= 15]
    df_second = df[df["day"] > 15]
    y_max = float(df["production_kwh"].max()) * 1.1

    def _daily_chart(data, title):
        return (
            alt.Chart(data)
            .mark_bar()
            .encode(
                x=alt.X("day:O",
                        title=i18n.t("fc.day_of", month=result["target_month_name"])),
                y=alt.Y(
                    "production_kwh:Q",
                    title=f"{i18n.t('fc.production')} ({i18n.t('unit.kwh')})",
                    scale=alt.Scale(domain=[0, y_max]),
                ),
                color=alt.Color(
                    "source:N",
                    title=i18n.t("fc.source"),
                    scale=alt.Scale(
                        domain=["API forecast", "Climate model"],
                        range=["#3cffaa", "#00d4ff"]
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("jalali_date:N", title=i18n.t("fc.jalali")),
                    alt.Tooltip("gregorian_date:N", title=i18n.t("fc.gregorian")),
                    alt.Tooltip("ghi:Q", title=i18n.t("fc.ghi")),
                    alt.Tooltip("production_kwh:Q", title=i18n.t("fc.production")),
                    alt.Tooltip("source:N", title=i18n.t("fc.source")),
                ],
            )
            .properties(height=330, title=title)
            .configure_view(strokeWidth=0)
            .configure_axis(
                gridColor="#2a4a3a",
                domainColor="#4a6a5a",
                labelColor="#a0d0b0",
            )
            .configure_title(color="#e0f0e8")
        )

    c1, c2 = st.columns(2)
    with c1:
        st.altair_chart(
            _daily_chart(df_first, i18n.t("fc.days_1_15")),
            use_container_width=True,
        )
        st.caption(i18n.t("fc.api_days_note", days=i18n.num(result["api_days"], 0)))
    with c2:
        st.altair_chart(
            _daily_chart(df_second, i18n.t("fc.days_16_plus")),
            use_container_width=True,
        )

    d1, d2 = st.columns(2)
    d1.metric(i18n.t("fc.avg_daily"),
              f"{i18n.num(df['production_kwh'].mean(), 1)} {i18n.t('unit.kwh')}")
    d2.metric(i18n.t("fc.peak_day"),
              f"{i18n.num(df['production_kwh'].max(), 1)} {i18n.t('unit.kwh')}")

    #revenue
    st.divider()
    st.subheader(i18n.t("rev.header"))
    price = st.number_input(
        i18n.t("rev.tariff"),
        min_value=0.0, value=25000.0, step=500.0,
    )
    income = pe.revenue(result["total_kwh"], price)

    r1, r2 = st.columns(2)
    r1.metric(i18n.t("rev.month_total", month=result["target_month_name"]),
              f"{i18n.num(income, 0)} {i18n.t('unit.irr')}")
    r2.metric(i18n.t("rev.avg_daily"),
              f"{i18n.num(income / result['days_in_month'], 0)} {i18n.t('unit.irr')}")

    #environmental impact
    st.divider()
    st.subheader(i18n.t("env.header", month=result["target_month_name"]))

    basis = result["total_kwh"]
    impact = pe.environmental_impact(basis)
    st.caption(i18n.t("env.basis", kwh=i18n.num(basis, 0), month=month_label))

    _cards([
        ("🪙", f"{i18n.num(impact['carbon_tokens'], 2)} {impact['token_symbol']}",
        i18n.t("env.tokens"),
        i18n.t("env.tokens_help", kg=i18n.num(pe.CARBON_TOKEN_UNIT_KG, 0))),
        ("♻️", f"{i18n.num(impact['carbon_saved_ton'], 3)} {i18n.t('unit.ton')}",
         i18n.t("env.co2"),
         i18n.t("env.co2_help", factor=i18n.num(pe.GRID_EMISSION_FACTOR, 2))),
        ("🌳", i18n.num(impact["trees_equivalent"], 1), i18n.t("env.trees"),
         i18n.t("env.trees_help", kg=i18n.num(pe.TREE_CO2_KG_PER_YEAR, 0))),
        ("🔋", f"{i18n.num(impact['ev_km'], 0)} {i18n.t('unit.km')}",
         i18n.t("env.car_range"),
         i18n.t("env.car_help", kwh=i18n.num(pe.EV_CONSUMPTION_KWH_PER_KM, 2))),
        ("⛽", f"{i18n.num(impact['gasoline_car_km'], 0)} {i18n.t('unit.km')}",
         i18n.t("env.gasoline"),
         i18n.t("env.gasoline_help", g=i18n.num(pe.CAR_CO2_PER_KM_G, 0))),
        ("🏠", i18n.num(impact["homes_powered"], 1), i18n.t("env.homes"),
         i18n.t("env.homes_help", kwh=i18n.num(pe.HOME_KWH_PER_MONTH, 0))),
    ])
    st.caption(i18n.t("env.token_badge"))

    #detail table
    with st.expander(i18n.t("tbl.header")):
        display = df.rename(columns={
            "day":             i18n.t("tbl.day"),
            "jalali_date":     i18n.t("fc.jalali"),
            "gregorian_date":  i18n.t("fc.gregorian"),
            "half":            i18n.t("tbl.segment"),
            "ghi":             i18n.t("fc.ghi"),
            "production_kwh":  f"{i18n.t('fc.production')} ({i18n.t('unit.kwh')})",
            "source":          i18n.t("fc.source"),
        })
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(
            f"{i18n.t('fc.geometry_factor')}: {result['geo_factor']}  |  "
            f"{i18n.t('fc.mount_factor')}: {result.get('mount_factor', '—')}  |  "
            f"{i18n.t('fc.panel_factor')}: {result.get('panel_factor', '—')}"
        )
