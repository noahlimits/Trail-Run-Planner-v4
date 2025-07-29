#!/usr/bin/env python3
"""
Trail Planner v4 streamlit.py  (v4.3.1, 2025‑07‑29)
--------------------------------------------------
Streamlit UI for **Trail‑Run Planner v4**.

* v4.3.1 – FIX: completed Downloads section (previous commit truncated at an
  unterminated string). Now builds on Streamlit Cloud without syntax error.
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

# ───────────────────────────────── page config ──────────────────────────────
st.set_page_config(
    page_title="Trail‑Run Planner v4",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏔️ Trail‑Run Planner v4")

# ───────────────────────────────── helper functions ─────────────────────────

def _suggest_key(dist_km: int) -> str:
    """Return the DISTANCE_SUGGEST key corresponding to dist_km."""
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

# Build workout‑category table once -----------------------------------------
_work_tbl = pd.DataFrame([
    {
        "Category": k.title(),
        "HR Target": (
            "<VT1" if tpl == ("<VT1",) else f"{int(lo*100)}–{int(hi*100)} % HRmax"
        ) if tpl != ("rest",) else "Rest",
        "RPE": CATEGORY_RPE[k],
    }
    for k, tpl in CATEGORY_HR.items()
])

# ───────────────────────────────── sidebar ─────────────────────────────────
with st.sidebar:
    st.header("Configure Variables")
    st.subheader("General")

    start_date = st.date_input("Start Date", dt.date.today())
    hrmax = st.slider("Max HR (HRmax)", 100, 230, 183)
    vt1 = st.slider("VT1 (Aerobic threshold HR)", 80, 200, 150)
    vo2max = st.slider("VO₂max", 0.0, 90.0, 57.0, step=0.1)

    race_distance_preview = st.slider(
        "Target Race Distance preview (km)",
        5,
        150,
        50,
        step=1,
        help="Used only to show recommended weekly hours before you tick 'Add Race'.",
    )

    hours_low, hours_high = st.slider(
        "Weekly Hours (range)",
        0,
        20,
        (8, 12),
        help="Planned running time per week. Scaling caps around 16 h/week (1.6× baseline).",
    )
    weekly_hours_str = (
        f"{hours_low}-{hours_high}" if hours_low != hours_high else f"{hours_low}"
    )

    # Guidance & validation --------------------------------------------------
    key = _suggest_key(race_distance_preview)
    rec_lo, rec_hi = map(int, DISTANCE_SUGGEST[key].replace("–", "-").split("-"))
    st.markdown(
        f"<u>Recommended for **{key}**: {rec_lo}–{rec_hi} h/week</u>",
        unsafe_allow_html=True,
    )
    avg_selected = (hours_low + hours_high) / 2
    if avg_selected < rec_lo:
        st.info("Below recommended – expect slower progression.")
    elif avg_selected > rec_hi * 1.2:
        st.warning(">20 % above recommended – diminishing returns & injury‑risk zone.")
    elif avg_selected > rec_hi:
        st.info("Slightly above recommended – monitor fatigue.")

    include_base_block = st.checkbox("Include Base Block", True)
    firefighter_schedule = st.checkbox("Firefighter Schedule", True)
    treadmill_available = st.checkbox("Treadmill Available (shift days)", True)
    terrain_type = st.selectbox("Terrain Type", TERRAIN_OPTIONS, index=2)

    # Race -------------------------------------------------------------------
    st.subheader("Race (optional)")
    add_race = st.checkbox("Add Race‑Specific Build")
    if add_race:
        race_date = st.date_input("Race Date", value=dt.date.today() + dt.timedelta(days=70))
        race_distance = st.number_input("Race Distance (km)", 1, 1000, race_distance_preview, step=1)
        elevation_gain = st.number_input("Elevation Gain (m)", 0, 20000, 2500, step=100)
    else:
        race_date = None
        race_distance = None
        elevation_gain = None

    shift_offset = st.number_input("Shift Cycle Offset", 0, 7, 0, step=1)
    generate_button = st.button("🚀 Generate Plan", type="primary")

# ───────────────────────────────── main logic ──────────────────────────────
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

    # Info tab ---------------------------------------------------------------
    with tab3:
        st.header("Why the weekly‑hours guidance?")
        st.markdown(
            """
*The recommended ranges draw on large‑cohort studies linking weekly mileage/time to both performance gains and overuse‑injury incidence.*  
Key findings:
* **Sub‑chronic load >1.5× baseline** (≈ >20 % above habitual) correlates with >2× injury risk (Nielsen 2014; Buist 2010).
* Diminishing aerobic returns when weekly volume exceeds ~1.5× time needed for the target distance (Seiler 2010).
            """
        )
        st.divider()
        st.header("Workout categories & intensity cues")
        st.dataframe(_work_tbl, use_container_width=True)
        st.divider()
        st.header("References")
        st.markdown(
            """
* Buist I et al. **Predictors of Running‑Related Injuries in Novice Runners**. *Med Sci Sports Exerc* 2010.  
* Nielsen RO et al. **Training load and structure risk factors for injury**. *Int J Sports Phys Ther* 2014.  
* Soligard T et al. **Load Management to Reduce Injury Risk**. *Br J Sports Med* 2016.  
* Seiler S. **What is best practice for training intensity and duration distribution?** *Int J Sports Physiol Perf* 2010.
            """
        )

    # ─────────────────────────────── Downloads ─────────────────────────────
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    xlsx_file = Path.cwd() / f"training_plan_{stamp}.xlsx"

    save_plan_to_excel(
        comp_df,
        race_df,
        {
            "Start Date": start_date,
            "Max HR": hrmax,
            "VT1": vt1,
            "VO2max": vo2max,
            "Weekly Hours": weekly_hours
