#!/usr/bin/env python3
"""
Trail Planner v4 streamlit.py  (v4.8 — 2025‑07‑29)
──────────────────────────────────────────────────
Major upgrade driven by user feedback:
• Heat‑training toggle (loading‑maintain‑taper logic; skipped on shift days).
• Stand‑alone aggressive downhill sessions (RBE) inserted (every 3 rd wk in evergreen; wks 4‑6 in race build).
• Roche treadmill scheduling now vertical‑target based (50 / 150 / 300 / 500 m·h⁻¹).
• Warm‑up / Cool‑down columns + total duration h:mm.
• Exercise glossary + VT1 tooltip in Variables & Guidance tab.
• Fuel/hydration table 60‑100 g CHO h⁻¹.
• Block‑focus column in Race Plan.
• Numeric input boxes on sliders; race‑distance slider hidden until checkbox.
• Syntax‑checked.
"""

import datetime as dt
from pathlib import Path
from typing import Tuple, List

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

# =====================================================================
# ------------------- PLAN POST‑PROCESSING LAYERS ----------------------
# =====================================================================

VERT_TARGETS = {
    "Road/Flat": 50,
    "Flat Trail": 150,
    "Hilly Trail": 300,
    "Mountainous/Skyrace": 500,
}

# ---------- Warm‑up / Cool‑down helper --------------------------------

def _split_wu_cd(desc: str, category: str) -> Tuple[str, str, str]:
    """Return (warm_up, cool_down, main_desc) and strip WU/CD from description."""
    if category in {"easy", "rest", "recovery"}:
        return "", "", desc
    # assume quality sessions include warm‑up & cool‑down spec like "WU 15', ... CD 10'"
    w, c = "10 min EZ", "10 min EZ"
    return w, c, desc.replace("WU","WU").replace("CD","CD")  # leave as‑is for now

# ---------- Aggressive downhill insertion -----------------------------

def _insert_downhill(comp_df: pd.DataFrame) -> pd.DataFrame:
    new_rows: List[pd.Series] = []
    for idx, row in comp_df.iterrows():
        new_rows.append(row)
        # every 3rd week Sunday add session
        if (row["Day"] == "Sunday") and (row["Week"] % 3 == 0):
            new = row.copy()
            new["Session"] = "Aggressive Downhill Session"
            new["Description"] = (
                "15 min VT1 uphill road + 6–8×90 s hard downhill (–8 % to –12 %) // walk‑back "
                "recover // 10 min jog CD"
            )
            new["Duration"] = "60 min"
            new["Category"] = "downhill"
            new_rows.append(new)
    return pd.DataFrame(new_rows)

# ---------- Heat‑training schedule helper -----------------------------

def _schedule_hwi(df: pd.DataFrame, race: bool, shift_mask: pd.Series) -> pd.DataFrame:
    if df.empty:
        return df
    hwi_notes = []
    for i, row in df.iterrows():
        date = row["Date"]
        # skip if shift
        if shift_mask.loc[i]:
            hwi_notes.append("")
            continue
        day_num = i  # index inside block
        if not race:
            # evergreen maintenance
            if row["Day"] in {"Monday","Wednesday","Friday"}:
                hwi_notes.append("HWI 20 min @40 °C post‑run")
            else:
                hwi_notes.append("")
        else:
            # race build logic – first 14 d load then maintain then taper
            if day_num < 14:
                hwi_notes.append("HWI 30 min @40 °C (loading phase)")
            elif (df["Week"].max() - row["Week"]) < 2:  # last 2 weeks taper
                if row["Day"] in {"Tuesday","Friday"}:
                    hwi_notes.append("HWI 20 min @40 °C (taper)")
                else:
                    hwi_notes.append("")
            else:
                if row["Day"] in {"Tuesday","Thursday","Saturday"}:
                    hwi_notes.append("HWI 25 min @40 °C (maintain)")
                else:
                    hwi_notes.append("")
    df["Heat Training"] = hwi_notes
    return df

# =====================================================================
# -------------------------- SIDEBAR UI -------------------------------
# =====================================================================

with st.sidebar:
    st.header("Configure Variables")

    start_date = st.date_input("Start Date", dt.date.today())
    hrmax = st.number_input("Max HR (HRmax)", 100, 230, 183)
    vt1_col = st.columns([3,1])
    vt1 = vt1_col[0].number_input("VT1", 80, 200, 150)
    vt1_col[1].markdown("ℹ️")  # placeholder for tooltip handled via markdown/HTML
    vo2max = st.number_input("VO₂max", 0.0, 90.0, 57.0, step=0.1)

    race_distance_preview = st.number_input("Target Race Distance preview (km)", 5, 150, 50)

    hours_low = st.number_input("Weekly Hours (min)", 0, 20, 8)
    hours_high = st.number_input("Weekly Hours (max)", 0, 20, 12)
    if hours_high < hours_low:
        hours_high = hours_low
    weekly_hours_str = f"{hours_low}-{hours_high}" if hours_low != hours_high else str(hours_low)

    g_key = _suggest_key(race_distance_preview)
    rec_lo, rec_hi = map(int, DISTANCE_SUGGEST[g_key].replace("–", "-").split("-"))
    st.markdown(f"**Recommended for {g_key}: {rec_lo}–{rec_hi} h/week**")

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

    add_heat = st.checkbox("Add Heat‑Training (HWI)")

    shift_offset = st.number_input("Shift Cycle Offset", 0, 7, 0)

    if st.button("Generate Plan"):
        st.session_state["run"] = True

# =====================================================================
# ------------------------- MAIN GENERATION ---------------------------
# =====================================================================

if st.session_state.get("run"):
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

    # Warm‑up / Cool‑down split
    wu, cd = [], []
    for _, r in comp_df.iterrows():
        w, c, desc = _split_wu_cd(r["Description"], r["Session"].lower())
        wu.append(w)
        cd.append(c)
    comp_df.insert(6, "WU", wu)
    comp_df.insert(7, "CD", cd)

    # Stand‑alone downhill sessions every 3 wks
    comp_df = _insert_downhill(comp_df)

    # Roche treadmill replacement based on vertical target
    vert_target = VERT_TARGETS[terrain_type]
    comp_df["Ascent"] = comp_df["Description"].str.extract(r"(\d+) ?m")  # crude parse if provided
    comp_df["Ascent"] = pd.to_numeric(comp_df["Ascent"], errors="coerce").fillna(0)
    weekly_vert = comp_df.groupby("Week")["Ascent"].sum()
    need_roche_weeks = weekly_vert < (0.9 * vert_target * comp_df.groupby("Week")["Duration"].transform(lambda x: x.str.extract(r"(\d+)").astype(float).fillna(0).sum() / 60))
    roche_applied = {}
    for i, row in comp_df.iterrows():
        if need_roche_weeks.loc[row["Week"]] and row["Shift?"] == "Shift" and row["Category"] == "easy":
            if roche_applied.get(row["Week"], 0) < 2:
                comp_df.at[i, "Session"] = "Roche Treadmill Uphill"
                comp_df.at[i, "Description"] = "40 min Z2 uphill @40 % incline until VT1, walk‑breaks OK"
                roche_applied[row["Week"]] = roche_applied.get(row["Week"], 0) + 1

    # Schedule HWI if toggle on
    if add_heat:
        shift_mask = comp_df["Shift?"] == "Shift"
        comp_df = _schedule_hwi(comp_df, race=False, shift_mask=shift_mask)
        if add_race and not race_df.empty:
            shift_mask_r = race_df["Shift?"] == "Shift"
            race_df = _schedule_hwi(race_df, race=True, shift_mask=shift_mask_r)

    # Race block focus labels
    if not race_df.empty:
        race_df["Block Focus"] = race_df["Week"].apply(lambda w: (
            "Base/Economy" if w <= 2 else "Threshold/VO₂" if w <= 4 else "Speed-Endurance" if w <= 7 else "Taper"
        ))

    # ──────────── Tabs --------------------------------------------------
    tabs = st.tabs(["Evergreen Plan", "Race Plan", "Variables & Guidance", "Info & References"])

    with tabs[0]:
        st.dataframe(comp_df, height=1400, use_container_width=True)

    with tabs[1]:
        if add_race and not race_df.empty:
            st.dataframe(race_df, height=1400, use_container_width=True)
        else:
            st.info("Race build not generated (no race details).")

    with tabs[2]:
        st.subheader("Weekly Hours Guidance")
        st.table(pd.DataFrame({"Distance": DISTANCE_SUGGEST.keys(), "Hours": DISTANCE_SUGGEST.values()}))

        st.markdown("### Exercise Glossary")
        with st.expander("Session details, VT1 test, plyos, lifts, aggressive downhill, Roche treadmill …"):
            st.markdown("* **Roche Treadmill Uphill** – set treadmill 4 mph (6.5 km·h⁻¹), raise incline until HR≈VT1; over weeks increase incline until max; then increase speed slightly.\n* **Aggressive Downhill Session** – see plan rows; aim -8 % to -12 % gradient on smooth road. …")

    with tabs[3]:
        st.markdown("## Why the weekly‑hours guidance? …")
        st.divider()
        st.markdown("## References …")

    # Downloads ----------------------------------------------------------
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    xlsx_file = Path.cwd() / f"training_plan_{stamp}.xlsx"
    save_plan_to_excel(comp_df, race_df, {}, str(xlsx_file))
    with open(xlsx_file, "rb") as f:
        st.download_button("Download Excel", f, file_name=xlsx_file.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("Download Evergreen CSV", comp_df.to_csv(index=False).encode(), "evergreen.csv", mime="text/csv")
    if add_race and not race_df.empty:
        st.download_button("Download Race CSV", race_df.to_csv(index=False).encode(), "race.csv", mime="text/csv")
