# Trail Run Training Plan Generator – Streamlit
# -------------------------------------------------
# A lightweight UI around `generate_training_plan_v4.py`.
# Drop this file next to that script (or install the package) and run:
#     streamlit run trail_plan_streamlit.py
# -------------------------------------------------

from datetime import date
from pathlib import Path
from io import BytesIO

import streamlit as st
import pandas as pd

# ---- local import ---------------------------------------------------- #
try:
    from generate_training_plan_v4 import generate_plan, save_plan_to_excel, TERRAIN_OPTIONS
except ImportError as err:
    st.error("Could not import `generate_training_plan_v4`. Make sure it lives in the same folder or in PYTHONPATH.")
    st.stop()

# --------------------------------------------------------------------- #
# ------------------------  Page Settings  ----------------------------- #
# --------------------------------------------------------------------- #
st.set_page_config(page_title="Trail Plan Generator", layout="wide")
st.title("🏃‍♂️ Trail‑Run Training‑Plan Generator")

st.markdown(
    """
    Fill in the variables below and click **Generate Plan**.
    The app will display previews of each sheet and offer an **XLSX** file for download.
    """
)

# --------------------------------------------------------------------- #
# --------------------------  Form Inputs  ----------------------------- #
# --------------------------------------------------------------------- #

with st.form(key="plan_form"):
    col_l, col_r = st.columns(2)

    # ---- left ------------------------------------------------------- #
    start_date = col_l.date_input("Start date", value=date.today())
    race_date  = col_l.date_input("Race date (optional)", value=None, min_value=date(1900, 1, 1))

    hrmax = col_l.number_input("Max HR (HRmax)", min_value=100, max_value=230, value=190)
    vt1   = col_l.number_input("VT1 (aerobic threshold HR)", min_value=60, max_value=200, value=150)
    vo2   = col_l.number_input("VO₂max (optional)", min_value=0.0, max_value=95.0, value=0.0, step=1.0)

    weekly_hours = col_l.text_input("Target weekly running time (e.g. '8-12' or '6')", value="8-12")

    include_base = col_l.checkbox("Include 12‑week base block", value=True)
    firefighter   = col_l.checkbox("Follow 48/96 firefighter shift logic", value=True)
    treadmill_avail = col_l.checkbox("Treadmill available on shift days", value=True)
    shift_offset = col_l.number_input("Shift cycle offset (0‑7)", min_value=0, max_value=7, value=0)

    # ---- right ------------------------------------------------------ #
    terrain = col_r.selectbox("Typical training terrain", TERRAIN_OPTIONS, index=TERRAIN_OPTIONS.index("Hilly Trail"))

    race_distance = col_r.number_input("Race distance (km)", min_value=0, step=1)
    elev_gain     = col_r.number_input("Race elevation gain (m)", min_value=0, step=100)

    submitted = st.form_submit_button(label="🚀 Generate Plan")

# --------------------------------------------------------------------- #
# ---------------------------  Action  -------------------------------- #
# --------------------------------------------------------------------- #

if submitted:
    # Validate dependent fields
    if race_date and (race_distance == 0 or elev_gain == 0):
        st.error("When a race date is provided you must also enter *race distance* and *elevation gain*.")
        st.stop()

    with st.spinner("Building your personalised plan …"):
        comp_df, race_df = generate_plan(
            start_date=start_date,
            hrmax=int(hrmax),
            vt1=int(vt1),
            vo2max=float(vo2),
            weekly_hours=weekly_hours,
            shift_offset=int(shift_offset),
            race_date=race_date if race_date.year > 1900 else None,
            race_distance_km=int(race_distance) if race_distance else None,
            elevation_gain_m=int(elev_gain) if elev_gain else None,
            terrain_type=terrain,
            include_base_block=include_base,
            firefighter_schedule=firefighter,
            treadmill_available=treadmill_avail,
        )

    # -------------------- Vars sheet dict --------------------------- #
    vars_sheet = {
        "Start Date": start_date.isoformat(),
        "Max HR (HRmax)": hrmax,
        "VT1": vt1,
        "VO2max": vo2,
        "Weekly Hours": weekly_hours,
        "Include Base Block": include_base,
        "Firefighter Schedule": firefighter,
        "Treadmill Available": treadmill_avail,
        "Terrain Type": terrain,
        "Race Date": race_date.isoformat() if race_date else "",
        "Race Distance (km)": race_distance or "",
        "Elevation Gain (m)": elev_gain or "",
        "Shift Offset": shift_offset,
    }

    # -------------------- Save to bytes ----------------------------- #
    buffer = BytesIO()
    # The helper expects a filename; give an in‑memory fake path then grab its bytes.
    tmp_path = Path("/tmp/training_plan.xlsx")
    save_plan_to_excel(comp_df, race_df, vars_sheet, str(tmp_path))
    buffer.write(tmp_path.read_bytes())
    buffer.seek(0)

    st.success("✅ Plan ready! Scroll down for previews or download below.")
    st.download_button(
        label="📥 Download XLSX plan",
        data=buffer,
        file_name="training_plan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # -------------------- Preview tables ---------------------------- #
    st.subheader("Comprehensive Plan (first 20 rows)")
    st.dataframe(comp_df.head(20))

    if not race_df.empty:
        st.subheader("Race‑specific Block (first 15 rows)")
        st.dataframe(race_df.head(15))

    # Offer to expand to full tables
    with st.expander("Show entire tables"):
        st.markdown("### Full Comprehensive Plan")
        st.dataframe(comp_df)
        if not race_df.empty:
            st.markdown("### Full Race Block")
            st.dataframe(race_df)
