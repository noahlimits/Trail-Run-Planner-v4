#!/usr/bin/env python3
"""
Trail Planner v4 streamlit.py  (v4.7 — 2025‑07‑29)
──────────────────────────────────────────────────
• Evergreen + optional Race builder
• Four tabs
• Downloads (Excel + CSV) section finalized
• Syntax verified with `python -m py_compile` — no errors.
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

# ───────────────────────── Page config ─────────────────────────
st.set_page_config(
    page_title="Trail‑Run Planner v4",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏔️ Trail‑Run Planner v4")

# ─────────────────── Helper functions ────────────────────────

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

# Workout category table --------------------------------------
_work_tbl = pd.DataFrame(
    [
        {
            "Category": k.title(),
            "HR Target": "<VT1" if tpl == ("<VT1",) else (
                "Rest" if tpl == ("rest",) else f"{int(tpl[0]*100)}–{int(tpl[1]*100)} % HRmax"
            ),
            "RPE": CATEGORY_RPE[k],
        }
        for k, tpl in CATEGORY_HR.items()
    ]
)

# ─────────────────── Sidebar inputs ──────────────────────────
with st.sidebar:
    st.header("Configure Variables")

    start_date = st.date_input("Start Date", dt.date.today())
    hrmax = st.slider("Max HR (HRmax)", 100, 230, 183)
    vt1 = st.slider("VT1", 80, 200, 150)
    vo2max = st.slider("VO₂max", 0.0, 90.0, 57.0, step=0.1)

    race_distance_preview = st.slider("Target Race Distance preview (km)", 5, 150, 50)

    hours_low, hours_high = st.slider("Weekly Hours", 0, 20, (8, 12))
    weekly_hours_str = f"{hours_low}-{hours_high}" if hours_low != hours_high else str(hours_low)

    g_key = _suggest_key(race_distance_preview)
    rec_lo, rec_hi = map(int, DISTANCE_SUGGEST[g_key].replace("–", "-").split("-"))
    st.markdown(f"**Recommended for {g_key}: {rec_lo}–{rec_hi} h/week**")

    include_base_block = st.checkbox("Include Base Block", True)
    firefighter_schedule = st.checkbox("Firefighter Schedule", True)
    treadmill_available = st.checkbox("Treadmill Available", True)
    terrain_type = st.selectbox("Terrain Type", TERRAIN_OPTIONS, index=2)

    add_race = st.checkbox("Add Race Build (optional)")
    if add_race:
        race_date = st.date_input("Race Date", dt.date.today() + dt.timedelta(days=70))
        race_distance = st.number_input("Race Distance (km)", 1, 1000, race_distance_preview)
        elevation_gain = st.number_input("Elevation Gain (m)", 0, 20000, 2500, step=100)
    else:
        race_date = race_distance = elevation_gain = None

    shift_offset = st.number_input("Shift Cycle Offset", 0, 7, 0)

    generate_button = st.button("Generate Plan")

# ─────────────────── Main generation ─────────────────────────
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

    tabs = st.tabs(["Evergreen Plan", "Race Plan", "Variables & Guidance", "Info & References"])

    # Evergreen
    with tabs[0]:
        st.dataframe(comp_df, height=1400, use_container_width=True)

    # Race
    with tabs[1]:
        if add_race and not race_df.empty:
            st.dataframe(race_df, height=1400, use_container_width=True)
        else:
            st.info("Race build not generated (no race details).")

    # Variables & Guidance
    with tabs[2]:
        var_df = pd.DataFrame(
            {
                "Variable": [
                    "Start Date", "Weekly Hours", "Terrain", "Include Base Block",
                    "Firefighter", "Treadmill", "Shift Offset", "VO₂max", "HRmax", "VT1",
                    "Race Date", "Race Distance", "Elevation Gain",
                ],
                "Value": [
                    start_date, weekly_hours_str, terrain_type, include_base_block,
                    firefighter_schedule, treadmill_available, shift_offset, vo2max,
                    hrmax, vt1, race_date, race_distance, elevation_gain,
                ],
            }
        )
        st.table(var_df)
        st.markdown("### Weekly Hours Guidance")
        st.table(pd.DataFrame({"Distance": DISTANCE_SUGGEST.keys(), "Hours": DISTANCE_SUGGEST.values()}))

    # Info & References
    with tabs[3]:
        st.markdown("## Why the weekly-hours guidance?")
        st.markdown(
            "Large cohort studies show weekly volume above ~1.5× baseline (>20 %) doubles injury risk "
            "and yields diminishing aerobic returns.")
        st.divider()
        st.markdown("## Workout categories & intensity cues")
        st.dataframe(_work_tbl, use_container_width=True)
        st.divider()
        st.markdown("## References")
        st.markdown("- Buist I et al. *Med Sci Sports Exerc* 2010.\n- Nielsen RO et al. *IJSPT* 2014.\n- Soligard T et al. *BJSM* 2016.\n- Seiler S. *IJSPP* 2010.")

    # Downloads
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    xlsx_file = Path.cwd() / f"training_plan_{stamp}.xlsx"
    save_plan_to_excel(
        comp_df,
        race_df,
        {
            "Start Date": start_date,
            "Weekly Hours": weekly_hours_str,
            "Terrain": terrain_type,
            "Include Base": include_base_block,
            "Firefighter": firefighter_schedule,
            "Treadmill": treadmill_available,
            "Shift Offset": shift_offset,
            "Race Date": race_date,
            "Race Distance": race_distance,
            "Elevation Gain": elevation_gain,
        },
        str(xlsx_file),
    )

    with open(xlsx_file, "rb") as f:
        st.download_button(
            label="Download Excel",
            data=f,
            file_name=xlsx_file.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.download_button("Download Evergreen CSV", comp_df.to_csv(index=False).encode(), "evergreen.csv", "text/csv")

    if add_race and not race_df.empty:
        st.download_button("Download Race CSV", race_df.to_csv(index=False).encode(), "race.csv", "text/csv")
