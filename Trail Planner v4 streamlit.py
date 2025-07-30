#!/usr/bin/env python3
"""
Trail-Run Planner v4 – Streamlit UI
version 5.5  (2025-07-30)
───────────────────────────────────────────────────────
Fully untruncated, complete implementation of all agreed features.
"""

from __future__ import annotations
import datetime as dt
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import streamlit as st

# Engine import
try:
    from generate_training_plan_v4 import (
        generate_plan,
        save_plan_to_excel,
        TERRAIN_OPTIONS,
    )
except ImportError:
    st.error("❌ Could not import generate_training_plan_v4.py. Place it alongside this file.")
    st.stop()

# Page config & splash
st.set_page_config(page_title="Trail-Run Planner v4", page_icon="🏔️", layout="wide")
st.title("🏔️ Trail-Run Planner v4")
st.caption("*No race? The 12-week evergreen block is tuned for events ≈ 30–50 km.*")

# Constants & helper tables
VERT_TARGETS = {
    "Road/Flat": 50,
    "Flat Trail": 150,
    "Hilly Trail": 300,
    "Mountainous/Skyrace": 500,
}

FUEL_TABLE = pd.DataFrame({
    "Condition": ["< 20 °C", "+10 °C", "+20 °C"],
    "CHO (g h⁻¹)": ["60–80", "70–90", "80–100"],
    "Fluid (ml h⁻¹)": ["500–600", "550–700", "600–800"],
})

GLOSSARY = {
    "Roche Treadmill Uphill": (
        "Set treadmill ≈ 6.5 km·h⁻¹ (4 mph). Raise incline until HR≈VT1; progress incline, then speed."
    ),
    "Hill Beast": "10/8/6/4/2 min uphill @ threshold; jog equal recoveries.",
    "Aggressive Downhill": (
        "15 min VT1 uphill + 6–8×90 s downhill (−8–12 %) walk-back + 10 min CD."
    ),
    "Plyometrics": (
        "Box jumps×6, bounds 30 m, skater bounds×10 ea, single-leg hops×10 ea — Base/Threshold:1 set; Speed:2 sets."
    ),
    "Heavy Lifts": (
        "Back-Squat or Bulgarian Split-Squat, Deadlift, RDL, Pull-ups — 3–4×5 @80–85% 1RM."
    ),
    "VT1 Test": (
        "Talk-test: first speech/breathing change = VT1; confirm HR drift <3% over 2×5-min."
    ),
}

DISTANCE_SUGGEST = {
    "10 km": "3–5",
    "21 km": "5–7",
    "42 km": "6–10",
    "50 km": "8–12",
    "70 km": "9–13",
    "100 km": "10–15",
}

# Sidebar inputs
with st.sidebar:
    st.header("Configure Variables")
    start_date = st.date_input("Start Date", dt.date.today())
    hrmax = st.number_input("Max HR (HRmax)", 100, 230, 185)
    c1, c2 = st.columns([3, 1])
    vt1 = c1.number_input("VT1 (bpm)", 80, 200, 150)
    c2.markdown(
        "<span title='See Variables & Guidance → Glossary for VT1 protocol'>ℹ️</span>",
        unsafe_allow_html=True,
    )
    vo2max = st.number_input("VO₂max", 0.0, 90.0, 57.0, step=0.5)

    preview_dist = st.number_input("Preview Race Distance (km)", 5, 150, 40)
    hrs_lo = st.number_input("Weekly Hours: low", 0, 20, 8)
    hrs_hi = st.number_input("Weekly Hours: high", 0, 20, 12)
    if hrs_hi < hrs_lo:
        hrs_hi = hrs_lo
    weekly_hours = f"{hrs_lo}-{hrs_hi}" if hrs_lo != hrs_hi else str(hrs_lo)

    def rec_key(km: int) -> str:
        if km <= 12:
            return "10 km"
        if km <= 30:
            return "21 km"
        if km <= 45:
            return "42 km"
        if km <= 60:
            return "50 km"
        if km <= 85:
            return "70 km"
        return "100 km"

    key = rec_key(preview_dist)
    lo, hi = map(int, DISTANCE_SUGGEST[key].split("–"))
    st.markdown(f"**Recommended for {key}: {lo}–{hi} h/week**")

    include_base = st.checkbox("Include 12-week Base block", True)
    firefighter = st.checkbox("48/96 Firefighter Schedule", True)
    treadmill_avail = st.checkbox("Treadmill available", True)
    terrain = st.selectbox("Typical terrain", TERRAIN_OPTIONS, index=2)

    add_race = st.checkbox("Add Race-specific Build")
    if add_race:
        race_date = st.date_input("Race Date", dt.date.today() + dt.timedelta(days=70))
        race_km = st.number_input("Race Distance (km)", 1, 1000, preview_dist)
        elev_gain = st.number_input("Elevation Gain (m)", 0, 20000, 2500, step=100)
    else:
        race_date = race_km = elev_gain = None

    add_heat = st.checkbox("Add Heat-Training (HWI)")
    shift_offset = st.number_input("Shift cycle offset", 0, 7, 0)
    run_btn = st.button("🚀 Generate Plan")

# Helper functions

def _split_wucd(cat: str) -> Tuple[str, str]:
    return ("", "") if cat in {"easy", "recovery", "rest"} else ("10 min EZ", "10 min EZ")


def _insert_downhill(df: pd.DataFrame) -> pd.DataFrame:
    out: List[pd.Series] = []
    for _, r in df.iterrows():
        out.append(r)
        if r["Day"] == "Sunday" and r["Week"] % 3 == 0:
            d = r.copy()
            d["Session"] = "Aggressive Downhill Session"
            d["Description"] = (
                "15 min VT1 uphill + 6–8×90 s downhill (−8–12%) walk-back + 10 min CD"
            )
            d["Duration"] = "60 min"
            d["Category"] = "downhill"
            out.append(d)
    return pd.DataFrame(out)


def _schedule_hwi(
    df: pd.DataFrame, is_race: bool, mask: pd.Series
) -> pd.DataFrame:
    notes: List[str] = []
    for i, r in df.iterrows():
        if mask.iloc[i]:
            notes.append("")
        elif is_race:
            if i < 14:
                notes.append("HWI 30 min @40 °C (load)")
            elif (df["Date"].max() - r["Date"]).days < 10 and r["Day"] in {"Tuesday", "Friday"}:
                notes.append("HWI 20 min @40 °C (taper)")
            else:
                notes.append("HWI 25 min @40 °C (maint)")
        else:
            if i < 10:
                notes.append("HWI 30 min @40 °C (load)")
            elif r["Day"] in {"Monday", "Wednesday", "Friday"}:
                notes.append("HWI 25 min @40 °C (maint)")
            else:
                notes.append("")
    df["Heat Training"] = notes
    return df


def _apply_roche(df: pd.DataFrame, terrain: str) -> pd.DataFrame:
    df["Ascent"] = pd.to_numeric(df["Description"].str.extract(r"(\d+)")[0], errors="coerce").fillna(0)
    weekly = df.groupby("Week")["Ascent"].sum()
    target = VERT_TARGETS[terrain]
    for wk, val in weekly.items():
        if val < 0.9 * target:
            mask = (
                (df["Week"] == wk)
                & (df["Shift?"] == "Shift")
                & (df["Category"] == "easy")
            )
            cnt = 0
            for idx in df[mask].index:
                if cnt >= 2:
                    break
                df.at[idx, "Session"] = "Roche Treadmill Uphill"
                df.at[idx, "Description"] = ("40 min Z2 uphill @40% incline until VT1; walk-breaks OK")
                cnt += 1
    return df

# Main UI
if run_btn:
    comp_df, race_df = generate_plan(
        start_date=start_date,
        hrmax=hrmax,
        vt1=vt1,
        vo2max=vo2max,
        weekly_hours=weekly_hours,
        shift_offset=shift_offset,
        race_date=race_date,
        race_distance_km=race_km,
        elevation_gain_m=elev_gain,
        terrain_type=terrain,
        include_base_block=include_base,
        firefighter_schedule=firefighter,
        treadmill_available=treadmill_avail,
    )
    # Evergreen post-process
    comp_df[["WU","CD"]] = pd.DataFrame(comp_df["Category"].apply(_split_wucd).tolist(), index=comp_df.index)
    comp_df = _insert_downhill(comp_df)
    comp_df = _apply_roche(comp_df, terrain)
    if add_heat:
        comp_df = _schedule_hwi(comp_df, False, comp_df["Shift?"] == "Shift")

    # Race post-process
    if add_race and not race_df.empty:
        race_df[["WU","CD"]] = pd.DataFrame(race_df["Category"].apply(_split_wucd).tolist(), index=race_df.index)
        race_df = _insert_downhill(race_df)
        race_df = _apply_roche(race_df, terrain)
        if add_heat:
            race_df = _schedule_hwi(race_df, True, race_df["Shift?"] == "Shift")
        race_df["Block Focus"] = race_df["Week"].apply(lambda w: "Base/Economy" if w <= 2 else ("Threshold/VO₂" if w <= 4 else ("Speed-Endurance" if w <= 7 else "Taper")))

    # Display tabs
    tabs = st.tabs(["Evergreen Plan","Race Plan","Variables & Guidance","Info & References"])
    with tabs[0]:
        st.dataframe(comp_df, use_container_width=True, height=800)
    with tabs[1]:
        if add_race and not race_df.empty:
            st.dataframe(race_df, use_container_width=True, height=800)
        else:
            st.info("Race build not generated.")
    with tabs[2]:
        st.subheader("Weekly Hours Guidance")
        st.table(pd.DataFrame({"Distance": list(DISTANCE_SUGGEST.keys()), "Hours": list(DISTANCE_SUGGEST.values())}))
        st.subheader("Fuel & Hydration Guidance")
        st.table(FUEL_TABLE)
        st.subheader("Exercise Glossary")
        for name, desc in GLOSSARY.items():
            st.markdown(f"**{name}** — {desc}")
    with tabs[3]:
        st.subheader("Block & Taper Rationale")
        st.markdown("*Base/Economy → Threshold/VO₂ → Speed-Endurance → 2-week taper.*")
        st.subheader("Shift-Cycle Explanation")
        st.markdown("Aligns long runs to Off days (48/96 shift schedule).")
        st.subheader("Heat-Training Background")
        st.markdown("Loading & maintenance as per Patterson 2021 & Casadio 2024; skip shift days.")
        st.subheader("References")
        st.markdown("""
* Patterson MJ et al. Scand J Med Sci Sports 2021.  
* Casadio JR et al. Front Physiol 2024.  
* Scheer & Vilalta-Franch J. Int J Sports Physiol Perf 2021.  
* Duarte J et al. Sports Med 2022.  
* Balsalobre-Fernández C et al. J Strength Cond Res 2020.  
* Jeukendrup A. Sports Sci Exchange 2024.  
* Mujika I. Int J Sports Physiol Perf 2020.  
""")
    # In-memory downloads
    buf = BytesIO()
    save_plan_to_excel(comp_df, race_df, {
        "Start Date": str(start_date),
        "HRmax": hrmax,
        "VT1": vt1,
        "Weekly Hours": weekly_hours,
        "Terrain": terrain,
        "Firefighter": firefighter,
        "Treadmill": treadmill_avail,
        **({} if not add_race else {"Race Date": str(race_date), "Race Distance (km)": race_km, "Elevation Gain": elev_gain}),
        **({} if not add_heat else {"Heat Training": True}),
    }, buf)
    buf.seek(0)
    st.download_button("Download XLSX Plan", buf, file_name="training_plan.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("Download Evergreen CSV", comp_df.to_csv(index=False).encode(), "evergreen.csv", mime="text/csv")
    if add_race and not race_df.empty:
        st.download_button("Download Race CSV", race_df.to_csv(index=False).encode(), "race.csv", mime="text/csv")
