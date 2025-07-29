import streamlit as st
import datetime as dt
import pandas as pd
from pathlib import Path

from generate_training_plan_v4 import generate_plan, save_plan_to_excel, _parse_date, TERRAIN_OPTIONS

st.title("🏃 Running Training Plan Generator")

# --- Sidebar inputs ---
st.sidebar.header("Variables")

start_date = st.sidebar.date_input("Start Date", dt.date.today())
hrmax = st.sidebar.number_input("Max HR (HRmax)", min_value=100, max_value=230, value=183)
vt1 = st.sidebar.number_input("VT1 (Aerobic threshold HR)", min_value=80, max_value=200, value=150)
vo2max = st.sidebar.number_input("VO₂max (optional)", min_value=0.0, max_value=90.0, value=57.0, step=0.1)
weekly_hours = st.sidebar.text_input("Weekly Hours (e.g. '8-12' or '6')", "8-12")

include_base_block = st.sidebar.checkbox("Include Base Block", True)
firefighter_schedule = st.sidebar.checkbox("Firefighter Schedule", True)
treadmill_available = st.sidebar.checkbox("Treadmill Available (non-firefighter only)", True)
terrain_type = st.sidebar.selectbox("Terrain Type", TERRAIN_OPTIONS, index=2)

race_date = st.sidebar.date_input("Race Date (optional)", value=None)
race_distance = st.sidebar.number_input("Race Distance (km)", min_value=0, step=1)
elevation_gain = st.sidebar.number_input("Elevation Gain (m)", min_value=0, step=100)
shift_offset = st.sidebar.number_input("Shift Cycle Offset", min_value=0, step=1, value=0)

if st.sidebar.button("Generate Plan"):
    comp_df, race_df = generate_plan(
        start_date=start_date,
        hrmax=hrmax,
        vt1=vt1,
        vo2max=vo2max,
        weekly_hours=weekly_hours,
        shift_offset=shift_offset,
        race_date=race_date if race_date != dt.date.today() else None,
        race_distance_km=race_distance if race_distance > 0 else None,
        elevation_gain_m=elevation_gain if elevation_gain > 0 else None,
        terrain_type=terrain_type,
        include_base_block=include_base_block,
        firefighter_schedule=firefighter_schedule,
        treadmill_available=treadmill_available,
    )

    st.subheader("Comprehensive (Evergreen) Plan")
    st.dataframe(comp_df)

    st.subheader("Race-Specific Plan")
    if race_df.empty:
        st.info("No race date provided or not enough info — Race Plan not generated.")
    else:
        st.dataframe(race_df)

    # Save Excel to temp and provide download
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    outfile = Path.cwd() / f"training_plan_{stamp}.xlsx"
    save_plan_to_excel(comp_df, race_df, {#!/usr/bin/env python3
"""
streamlit_app.py
----------------
Interactive Streamlit UI for ``generate_training_plan_v4.py``.

Run locally with:
    streamlit run streamlit_app.py

All widgets live in the sidebar, so users can tweak inputs repeatedly and
instantly preview changes.  Sliders, date pickers, and check‑boxes replace the
original CLI ``input()`` prompts.  Outputs appear in two tabs (Evergreen & Race)
and can be downloaded as Excel or CSV.
"""

import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

from generate_training_plan_v4 import (
    generate_plan,
    save_plan_to_excel,
    TERRAIN_OPTIONS,
)

# ---------------------------------------------------------------------------
# 🖼️  Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Training Plan Generator",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏃 Training Plan Generator")

# ---------------------------------------------------------------------------
# 🔧 Sidebar — user inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Configure Variables")

    # --- General block ------------------------------------------------------
    st.subheader("General")
    start_date = st.date_input("Start Date", dt.date.today())

    hrmax = st.slider("Max HR (HRmax)", 100, 230, 183)
    vt1 = st.slider("VT1 (Aerobic threshold HR)", 80, 200, 150)
    vo2max = st.slider("VO₂max", 0.0, 90.0, 57.0, step=0.1)

    hours_low, hours_high = st.slider(
        "Weekly Hours (range)",
        0,
        20,
        (8, 12),
        help="Planned running time per week (hours)",
    )
    weekly_hours_str = (
        f"{hours_low}-{hours_high}" if hours_low != hours_high else f"{hours_low}"
    )

    include_base_block = st.checkbox("Include Base Block", True)
    firefighter_schedule = st.checkbox("Firefighter Schedule", True)
    treadmill_available = st.checkbox("Treadmill Available (for shift days)", True)

    terrain_type = st.selectbox("Terrain Type", TERRAIN_OPTIONS, index=2)

    # --- Race block ---------------------------------------------------------
    st.subheader("Race (optional)")
    add_race = st.checkbox("Add Race‑Specific Build")
    if add_race:
        race_date = st.date_input(
            "Race Date", value=dt.date.today() + dt.timedelta(days=70)
        )
        race_distance = st.number_input("Race Distance (km)", 1, 1000, 50, step=1)
        elevation_gain = st.number_input("Elevation Gain (m)", 0, 20000, 2500, step=100)
    else:
        race_date = None
        race_distance = None
        elevation_gain = None

    shift_offset = st.number_input(
        "Shift Cycle Offset", min_value=0, max_value=7, value=0, step=1
    )

    generate_button = st.button("🚀 Generate Plan", type="primary")

# ---------------------------------------------------------------------------
# 🏗️  Generate plan + display
# ---------------------------------------------------------------------------
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

    tab1, tab2 = st.tabs(["Evergreen Plan", "Race Plan"])

    with tab1:
        st.dataframe(comp_df, use_container_width=True)

    with tab2:
        if add_race and not race_df.empty:
            st.dataframe(race_df, use_container_width=True)
        else:
            st.info("No race details provided – Race Plan not generated.")

    # -----------------------------------------------------------------------
    # 💾 Downloads
    # -----------------------------------------------------------------------
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    xlsx_file = Path.cwd() / f"training_plan_{stamp}.xlsx"

    save_plan_to_excel(
        comp_df,
        race_df,
        {
            "Start Date": start_date,
            "Max HR (HRmax)": hrmax,
            "VT1": vt1,
            "VO2max": vo2max,
            "Weekly Hours": weekly_hours_str,
            "Include Base Block": include_base_block,
            "Firefighter Schedule": firefighter_schedule,
            "Treadmill Available": treadmill_available,
            "Terrain Type": terrain_type,
            "Race Date": race_date,
            "Race Distance (km)": race_distance,
            "Elevation Gain (m)": elevation_gain,
            "Shift Offset": shift_offset,
        },
        str(xlsx_file),
    )

    with open(xlsx_file, "rb") as f:
        st.download_button(
            "⬇️ Download Excel Plan",
            f,
            xlsx_file.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.download_button(
        "Download Evergreen CSV",
        comp_df.to_csv(index=False).encode(),
        "evergreen_plan.csv",
        mime="text/csv",
    )

    if add_race and not race_df.empty:
        st.download_button(
            "Download Race CSV",
            race_df.to_csv(index=False).encode(),
            "race_plan.csv",
            mime="text/csv",
        )

        "Start Date": start_date,
        "Max HR (HRmax)": hrmax,
        "VT1": vt1,
        "VO2max": vo2max,
        "Weekly Hours": weekly_hours,
        "Include Base Block": include_base_block,
        "Firefighter Schedule": firefighter_schedule,
        "Treadmill Available": treadmill_available,
        "Terrain Type": terrain_type,
        "Race Date": race_date,
        "Race Distance (km)": race_distance,
        "Elevation Gain (m)": elevation_gain,
        "Shift Offset": shift_offset,
    }, str(outfile))

    with open(outfile, "rb") as f:
        st.download_button(
            label="⬇️ Download Excel Plan",
            data=f,
            file_name=outfile.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
