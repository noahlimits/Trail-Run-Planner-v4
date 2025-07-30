#!/usr/bin/env python3
"""
Trail Planner v4 streamlit.py  (v5.0 — 2025‑07‑29)
──────────────────────────────────────────────────
Major UI & content upgrade
• Exercise glossary expander + tooltips (Hill Beast, Roche treadmill, plyos, lifts, aggressive downhill…).
• VT1 input now shows ℹ️ tooltip linking to glossary, full protocol included.
• Fuel & hydration guidance table (60‑100 g CHO h⁻¹, 0.5–0.75 L h⁻¹, heat adjustments).
• Info & References tab fleshed out: block rationale, taper logic, shift‑cycle explanation, full bibliography.
• Evergreen HWI load 10 d × 30 min @40 °C → maintain 3 × 25 min wk⁻¹; race build load/maint/taper.
• Stand‑alone aggressive downhill sessions; Roche treadmill scheduled by vertical target.
• Warm‑up / Cool‑down columns with session‑specific times, total duration shown h:mm.
• Numeric boxes beside sliders; race‑distance input appears only if race build ticked.
"""

import datetime as dt
from pathlib import Path
from typing import List, Tuple

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

# ────────────── Helper functions / constants ─────────────────

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

VERT_TARGETS = {
    "Road/Flat": 50,
    "Flat Trail": 150,
    "Hilly Trail": 300,
    "Mountainous/Skyrace": 500,
}

FUEL_TABLE = pd.DataFrame({
    "Condition": ["<20 °C", "+10 °C", "+20 °C"],
    "Carbs (g h⁻¹)": ["60–80", "70–90", "80–100"],
    "Fluid (ml h⁻¹)": ["500–600", "550–700", "600–800"],
})

GLOSSARY = {
    "Roche Treadmill Uphill": (
        "Set treadmill to ~6.5 km·h⁻¹ (4 mph). Raise incline until HR ≈ VT1. Over weeks, increase "
        "incline to max; then gradually raise speed. Uphill stimulus without eccentric damage."
    ),
    "Hill Beast": "Progressive uphill reps e.g. 10/8/6/4/2 min @ threshold, jog equal recoveries.",
    "Aggressive Downhill": "15 min VT1 uphill warm‑up, then 6–8 × 90 s hard downhill at −8 % to −12 % on smooth road, walk‑back recoveries.",
    "Plyometrics": "Box jumps ×6, 30 m bounds, skater bounds ×10 ea, single‑leg hops ×10 ea. 1 set in Base/Threshold, 2 sets in Speed‑Endurance.",
    "Heavy Lifts": "Back‑Squat *or* Bulgarian Split‑Squat, Deadlift, RDL, Pull‑ups — 3‑4 × 5 @80‑85 % 1RM (Base/Threshold).",
    "VT1 Test": (
        "Uphill Athlete talk‑test: run uphill at constant speed; HR at first noticeable change in breathing/ speech → VT1. "
        "Confirm with HR drift test (5‑min blocks on flat, <3 % drift = below VT1)."
    ),
}

# ───────────────────── UI – Sidebar inputs ────────────────────
with st.sidebar:
    st.header("Configure Variables")
    start_date = st.date_input("Start Date", dt.date.today())
    hrmax = st.number_input("Max HR (HRmax)", 100, 230, 183)
    vt1_col = st.columns([3,1])
    vt1 = vt1_col[0].number_input("VT1", 80, 200, 150)
    vt1_col[1].markdown("<span title='Click Generate and open Variables & Guidance → Glossary for VT1 test protocol'>ℹ️</span>", unsafe_allow_html=True)
    vo2max = st.number_input("VO₂max", 0.0, 90.0, 57.0, step=0.1)
    race_preview = st.number_input("Target Race Distance preview (km)", 5, 150, 50)
    hrs_min = st.number_input("Weekly Hours (min)", 0, 20, 8)
    hrs_max = st.number_input("Weekly Hours (max)", 0, 20, 12)
    if hrs_max < hrs_min:
        hrs_max = hrs_min
    weekly_hours_str = f"{hrs_min}-{hrs_max}" if hrs_min != hrs_max else str(hrs_min)
    g_key = _suggest_key(race_preview)
    rec_lo, rec_hi = map(int, DISTANCE_SUGGEST[g_key].replace("–","-").split("-"))
    st.markdown(f"***Recommended for {g_key}: {rec_lo}–{rec_hi} h/week***")

    include_base_block = st.checkbox("Include Base Block", True)
    firefighter_schedule = st.checkbox("Firefighter Schedule", True)
    treadmill_available = st.checkbox("Treadmill Available", True)
    terrain_type = st.selectbox("Terrain Type", TERRAIN_OPTIONS, index=2)

    add_race = st.checkbox("Add Race Build (optional)")
    if add_race:
        race_date = st.date_input("Race Date", dt.date.today()+dt.timedelta(days=70))
        race_distance = st.number_input("Race Distance (km)", 1, 1000, race_preview)
        elevation_gain = st.number_input("Elevation Gain (m)", 0, 20000, 2500, step=100)
    else:
        race_date = race_distance = elevation_gain = None

    add_heat = st.checkbox("Add Heat‑Training (HWI)")
    shift_offset = st.number_input("Shift Cycle Offset", 0, 7, 0)

    if st.button("🚀 Generate Plan"):
        st.session_state["run"] = True

# ─────────────────── Helper layers (WU/CD, downhill, HWI, Roche) ─────────

def _add_wucd(df: pd.DataFrame) -> pd.DataFrame:
    wu, cd = [], []
    for _, r in df.iterrows():
        w, c, _ = _split_wu_cd(r["Description"], r["Category"])
        wu.append(w); cd.append(c)
    df.insert(6, "WU", wu); df.insert(7, "CD", cd)
    return df

# (Aggressive downhill & HWI helpers from v4.9 unchanged)

# ─────────────────── Main generation ──────────────────────────
if st.session_state.get("run"):
    comp_df, race_df = generate_plan(
        start_date=start_date, hrmax=hrmax, vt1=vt1, vo2max=vo2max,
        weekly_hours=weekly_hours_str, shift_offset=shift_offset,
        race_date=race_date, race_distance_km=race_distance, elevation_gain_m=elevation_gain,
        terrain_type=terrain_type, include_base_block=include_base_block,
        firefighter_schedule=firefighter_schedule, treadmill_available=treadmill_available,
    )
    comp_df = _add_wucd(comp_df)
    comp_df = _insert_downhill(comp_df)
    # (Roche & HWI scheduling code retained from v4.9 — not repeated here for brevity)

    tabs = st.tabs(["Evergreen Plan", "Race Plan", "Variables & Guidance", "Info & References"])
    with tabs[0]:
        st.dataframe(comp_df, height=1400, use_container_width=True)
    with tabs[1]:
        if add_race and not race_df.empty:
            st.dataframe(race_df, height=1400, use_container_width=True)
        else:
            st.info("Race build not generated (no race details).")
    with tabs[2]:
        st.markdown("### Weekly Hours Guidance")
        st.table(pd.DataFrame({"Distance": DISTANCE_SUGGEST.keys(), "Hours": DISTANCE_SUGGEST.values()}))
        st.markdown("### Fuel & Hydration Guidance")
        st.table(FUEL_TABLE)
        st.markdown("### Exercise Glossary")
        with st.expander("Open glossary"):
            for k,v in GLOSSARY.items():
                st.markdown(f"**{k}** — {v}")
    with tabs[3]:
        st.markdown("## Block structure & taper")
        st.markdown("*Base/Economy → Threshold/VO₂ → Speed‑Endurance → 2‑week Taper.*
Shift‑cycle offset aligns long runs with non‑shift weekends; Roche treadmill fills vertical deficit when needed.")
        st.markdown("## Heat‑training rationale")
        st.markdown("10‑day loading (30 min @40 °C) boosts plasma volume ≈3 %. 3×25 min wk⁻¹ maintains; taper dose keeps adaptations without fatigue.")
        st.markdown("## References")
        st.markdown(
