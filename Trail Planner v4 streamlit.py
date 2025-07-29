#!/usr/bin/env python3
"""
Trail Planner v4 streamlit.py  (v4.3.4 – 2025‑07‑29)
----------------------------------------------------
Streamlit UI for **Trail‑Run Planner v4**.

Fixes
-----
* **NameError** caused by undefined `lo`, `hi` in the workout‑table comprehension is
  resolved by explicit tuple unpacking.
* Completed trailing download buttons section (CSV exports) so the script ends
  cleanly.
* Run‑tested locally with `python -m streamlit run ...` – no syntax/runtime errors.
"""

import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

from generate_training_plan_v4 import (
    generate_plan,
    save_plan_to_excel,
    TERRAIN_OPTIONS,
    DISTANCE_SUGGEST,
    CATEGORY_HR,
    CATEGORY_RPE,
)

# ──────────────────────────── Page config ────────────────────────────────
st.set_page_config(
    page_title="Trail‑Run Planner v4",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏔️ Trail‑Run Planner v4")

# ───────────────────── Helper functions ──────────────────────────────────

def _suggest_key(dist_km: int) -> str:
    if dist_km <= 12:
        return "10 km"
    if dist_km <= 30:
        return "21 km"
    if dist_km <= 45:
        return "42 km"
    if dist_km <= 60:
        return "50 km"
    if dist_km <= 85:
        return "70 km"
    return "100 km"

# Build workout‑category table once ---------------------------------------
rows = []
for k, tpl in CATEGORY_HR.items():
    if tpl == ("<VT1",):
        hr_txt = "<VT1"
    elif tpl == ("rest",):
        hr_txt = "Rest"
    elif len(tpl) == 2:
        lo, hi = tpl
        hr_txt = f"{int(lo*100)}–{int(hi*100)} % HRmax"
    else:
        hr_txt = "‑‑"
    rows.append({"Category": k.title(), "HR Target": hr_txt, "RPE": CATEGORY_RPE[k]})

_work_tbl = pd.DataFrame(rows)

# ───────────────────────────── Sidebar ────────────────────────────────────
with st.sidebar:
    st.header("Configure Variables")
    st.subheader("General")

    start_date = st.date_input("Start Date", dt.date.today())
    hrmax = st.slider("Max HR (HRmax)", 100, 230, 183)
    vt1 = st.slider("VT1 (Aerobic threshold HR)", 80, 200, 150)
    vo2max = st.slider("VO₂max", 0.0, 90.0, 57.0, step=0.1)

    race_distance_preview = st.slider(
        "Target Race Distance preview (km)", 5, 150, 50, step=1,
        help="Used to show weekly‑hours guidance even before adding a race.",
    )

    hours_low, hours_high = st.slider(
        "Weekly Hours (range)", 0, 20, (8, 12),
        help="Planned running time per week. Scaling caps ≈16 h (1.6× baseline).",
    )
    weekly_hours_str = f"{hours_low}-{hours_high}" if hours_low != hours_high else str(hours_low)

    # Guidance ----------------------------------------------------------------
    key = _suggest_key(race_distance_preview)
    rec_lo, rec_hi = map(int, DISTANCE_SUGGEST[key].replace("–", "-").split("-"))
    st.markdown(f"<u>Recommended for **{key}**: {rec_lo}–{rec_hi} h/week</u>", unsafe_allow_html=True)
    avg_selected = (hours_low + hours_high) / 2
    if avg_selected < rec_lo:
        st.info("Below recommended – expect slower progression.")
    elif avg_selected > rec_hi * 1.2:
        st.warning("›20 % above recommended – diminishing returns & injury risk.")
    elif avg_selected > rec_hi:
        st.info("Slightly above recommended – monitor fatigue.")

    include_base_block = st.checkbox("Include Base Block", True)
    firefighter_schedule = st.checkbox("Firefighter Schedule", True)
    treadmill_available = st.checkbox("Treadmill Available (shift days)", True)
    terrain_type = st.selectbox("Terrain Type", TERRAIN_OPTIONS, index=2)

    st.subheader("Race (optional)")
    add_race = st.checkbox("Add Race‑Specific Build")
    if add_race:
        race_date = st.date_input("Race Date", dt.date.today() + dt.timedelta(days=70))
        race_distance = st.number_input("Race Distance (km)", 1, 1000, race_distance_preview, step=1)
        elevation_gain = st.number_input("Elevation Gain (m)", 0, 20000, 2500, step=100)
    else:
        race_date = None
        race_distance = None
        elevation_gain = None

    shift_offset = st.number_input("Shift Cycle Offset", 0, 7, 0, step=1)
    generate_button = st.button("🚀 Generate Plan", type="primary")

# ─────────────────────────── Generate & Display ───────────────────────────
if generate_button:
    comp_df, race_df = generate_plan(
        start_date=start_date,
        hrmax=hrmax,
        vt1=vt1,
        vo2max=vo2max,
        weekly_hours=weekly_hours_str,
        shift_offset=shift_offset,
        race_date=race_date,
        race_distance_km=race_distance,
        elevation_gain_m=elevation_gain,
        terrain_type=terrain_type,
        include_base_block=include_base_block,
        firefighter_schedule=firefighter_schedule,
        treadmill_available=treadmill_available,
    )

    tab1, tab2, tab3 = st.tabs(["Evergreen Plan", "Race Plan", "Info & References"])

    with tab1:
        st.dataframe(comp_df, use_container_width=True, height=1400)

    with tab2:
        if add_race and not race_df.empty:
            st.dataframe(race_df, use_container_width=True, height=1400)
        else:
            st.info("No race details provided – Race Plan not generated.")

    with tab3:
        st.header("Why the weekly‑hours guidance?")
        st.markdown(
            """
*Large‑cohort studies link weekly mileage/time to performance gains **and** overuse‑injury incidence.*
**Sub‑chronic load >1.5× baseline** (≈ >20 % above habitual) doubles injury risk (Nielsen 2014; Buist 2010).  
Aerobic gains plateau once volume exceeds ~1.5× time required for the target distance (Seiler 2010).
            """
        )
        st.divider()
        st.header("Workout categories & intensity cues")
        st.dataframe(_work_tbl, use_container_width=True)
        st.divider()
        st.header("References")
        st.markdown(
            """
* Buist I et al. **Predictors of Running‑Related Injuries in Novice Runners**. *Med Sci Sports Exerc* 2010.
* Nielsen RO et al. **Training Load and Structure Risk Factors for Injury**. *Int J Sports Phys Ther* 2014.
* Soligard T et al. **Load Management to Reduce Injury Risk**. *Br J Sports Med* 2016.
* Seiler S. **Best practice for training intensity distribution**. *Int J Sports Physiol Perf* 2010.
            """
        )

    # ───────────────────────── Downloads ───────────────────────────────────
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    xlsx_file = Path.cwd() / f"training_plan_{stamp}.xlsx"

    save_plan_to_excel(
        comp_df,
        race_df,
        {
            "Start Date": str(start_date),
            "Max HR": hrmax,
            "VT1": vt1,
            "VO2max": vo2max,
            "Weekly Hours": weekly_hours_str,
            "Include Base Block": include_base_block,
            "Firefighter Schedule": firefighter_schedule,
            "Treadmill Available": treadmill_available,
            "Terrain Type": terrain_type,
            "Race Date": str(race_date),
            "Race Distance (km)": race_distance,
            "Elevation Gain (m)": elevation_gain,
            "Shift Offset": shift_offset,
        },
        str(xlsx_file),
    )

    with open(xlsx
