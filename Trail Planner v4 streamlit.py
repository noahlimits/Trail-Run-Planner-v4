#!/usr/bin/env python3
"""
Trail Planner v4 streamlit.py  (v5.6 — 2025-07-30)
──────────────────────────────────────────────────
Complete implementation with all agreed features:
• Evergreen + optional Race builder with proper heat training phases
• Heat training toggle with loading/maintenance/taper phases
• Standalone aggressive downhill sessions with RBE protocol
• Roche treadmill vs Easy run optimization based on vertical targets
• WU/CD columns with session-specific guidance
• Exercise glossary with tooltips and full explanations
• VT1 hover help and fuel/hydration guidance
• Four tabs: Evergreen, Race Plan, Variables & Guidance, Info & References
• In-memory XLSX downloads (no temp files)
• Race distance slider only appears when race build selected
• Numeric input boxes alongside sliders
"""

import datetime as dt
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pandas as pd
import streamlit as st

# Engine import
try:
    from generate_training_plan_v4 import (
        generate_plan,
        save_plan_to_excel,
        TERRAIN_OPTIONS,
        DISTANCE_SUGGEST,
        CATEGORY_HR,
        CATEGORY_RPE,
    )
except ImportError:
    st.error("❌ Could not import generate_training_plan_v4.py. Place it alongside this file.")
    st.stop()

# ───────────────────────── Page config ─────────────────────────
st.set_page_config(
    page_title="Trail-Run Planner v4",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏔️ Trail-Run Planner v4")
st.caption("*No race? The 12-week evergreen block is tuned for trail events ≈ 30–50 km.*")

# ───────────────────────── Constants & Tables ─────────────────────────
VERT_TARGETS = {
    "Road/Flat": 50,
    "Flat Trail": 150, 
    "Hilly Trail": 300,
    "Mountainous/Skyrace": 500
}

FUEL_TABLE = pd.DataFrame({
    "Condition": ["< 20°C (baseline)", "+10°C above 20°C", "+20°C above 20°C"],
    "CHO (g/hr)": ["60-90", "66-99", "72-108"],
    "Fluid (ml/hr)": ["500-750", "550-825", "600-900"]
})

GLOSSARY = {
    "Hill Beast": "Sustained uphill intervals at threshold effort (85-95% HRmax). Find a 4-8% grade hill or set treadmill incline. Work intervals 8-20 minutes with 2-3 minute recoveries.",
    
    "Threshold Hills": "Moderate uphill efforts at tempo pace (80-85% HRmax). Less intense than Hill Beast but still challenging. Good for building aerobic power on climbs.",
    
    "Downhill Reps": "Short, controlled downhill efforts (30-90 seconds) on -8% to -12% grade. Focus on cadence and control, not speed. Builds eccentric strength and teaches downhill running economy.",
    
    "Roche Treadmill": "Set treadmill to 4 mph (6.4 km/h). Begin run and gradually increase incline until VT1 heart rate is reached. Over time, increase incline to maximum (usually 15%). Only after reaching max incline should you increase speed. Builds aerobic power efficiently.",
    
    "Strides": "6-8 x 20-30 second accelerations on flat ground. Start easy, build to fast (not sprint), then decelerate. 60-90 second easy jog recovery. Focus on form and turnover.",
    
    "Hill Strides": "Similar to strides but on 4-6% uphill grade. Slightly shorter (15-20 seconds) due to increased effort. Builds power and improves uphill running form.",
    
    "Plyometrics": "Explosive exercises done after main run: Box jumps x6, Bounding x30m, Skater bounds x10 each leg, Single-leg hops x10 each leg. 1-2 sets depending on training block.",
    
    "Heavy Lifts": "Compound movements for trail runners. Choose: Back Squat OR Bulgarian Split Squat, plus Deadlift, Romanian Deadlift, Pull-ups. Base/Threshold: 3-4 x 5 @ 80-85% 1RM. Speed-Endurance: 2 x 3 Power Cleans @ 70% + plyos.",
    
    "Aggressive Downhill": "Standalone session for repeated bout effect (RBE). 15min VT1 uphill warm-up, then 6-8 x 90sec hard downhill on smooth road (-8% to -12% grade), walk-back recovery, 10min easy cool-down. Builds eccentric strength safely.",
    
    "VT1 (Aerobic Threshold)": "First ventilatory threshold - the point where breathing becomes noticeably harder but you can still maintain conversation. Test: Run on flat ground starting easy, increase pace every 2 minutes until breathing shifts from purely nasal to mouth breathing. Note HR at this transition."
}

# ───────────────────────── Helper Functions ─────────────────────────
def _suggest_key(dist_km: int) -> str:
    """Map distance to weekly hours recommendation key"""
    if dist_km <= 12: return "10 km"
    if dist_km <= 30: return "21 km" 
    if dist_km <= 45: return "42 km"
    if dist_km <= 60: return "50 km"
    if dist_km <= 85: return "70 km"
    return "100 km"

def _split_wucd(session_type: str) -> Tuple[str, str]:
    """Return warm-up and cool-down for session type"""
    if session_type in ["Hill Beast", "Threshold Hills", "Downhill Reps", "Roche Treadmill"]:
        return "10min EZ + drills", "10min EZ"
    elif session_type in ["Strides", "Hill Strides"]:
        return "15min EZ + drills", "5min EZ"
    elif session_type == "Aggressive Downhill":
        return "15min VT1 uphill", "10min EZ jog"
    elif "Lift" in session_type or "Plyo" in session_type:
        return "10min dynamic", "5min stretch"
    else:  # Easy runs
        return "", ""  # Implicit 5min roll-in/out

def _insert_downhill(df: pd.DataFrame, is_race_build: bool = False) -> pd.DataFrame:
    """Insert standalone aggressive downhill sessions"""
    if df.empty:
        return df
        
    df = df.copy()
    
    # Debug: print column names to understand structure
    print(f"DataFrame columns: {df.columns.tolist()}")
    if not df.empty:
        print(f"Sample row: {df.iloc[0].to_dict()}")
    
    # Handle different possible column names for day
    day_col = None
    if 'Day' in df.columns:
        day_col = 'Day'
    elif 'Day_of_Week' in df.columns:
        day_col = 'Day_of_Week'
    elif 'Weekday' in df.columns:
        day_col = 'Weekday'
    
    if day_col is None or 'Week' not in df.columns:
        st.warning("Cannot insert downhill sessions: missing Day or Week columns")
        return df
    
    if is_race_build:
        # Weekly in weeks 4-6 of race build
        downhill_weeks = [4, 5, 6]
        for week in downhill_weeks:
            week_mask = df['Week'] == week
            if week_mask.any():
                # Try to find Tuesday (day 2) or any available day
                week_df = df[week_mask]
                if len(week_df) > 1:  # Has multiple days
                    idx = week_df.index[1]  # Use second day of week
                    df.loc[idx, 'Session'] = "Aggressive Downhill"
                    df.loc[idx, 'Duration'] = "45min"
                    df.loc[idx, 'Description'] = "15min VT1 uphill + 6x90s hard downhill (-10% road) + 10min CD"
    else:
        # Every 3rd week in evergreen
        downhill_weeks = [3, 6, 9, 12]
        for week in downhill_weeks:
            week_mask = df['Week'] == week
            if week_mask.any():
                # Find a suitable day for the downhill session
                week_df = df[week_mask]
                if not week_df.empty:
                    # Use the last day of the week for downhill session
                    target_idx = week_df.index[-1]
                    
                    # Create new row for aggressive downhill
                    new_row = df.loc[target_idx].copy()
                    new_row['Session'] = "Aggressive Downhill"
                    new_row['Duration'] = "45min"
                    new_row['Description'] = "RBE session: 6x90s downhill reps"
                    
                    # Add new row to dataframe
                    df = pd.concat([df, new_row.to_frame().T], ignore_index=True)
    
    return df.sort_values(['Week', day_col] if day_col in df.columns else ['Week']).reset_index(drop=True)

def _apply_roche(df: pd.DataFrame, terrain: str, treadmill_avail: bool) -> pd.DataFrame:
    """Replace easy runs with Roche treadmill based on weekly vertical targets"""
    if not treadmill_avail or df.empty:
        return df
        
    df = df.copy()
    target_vert_per_hour = VERT_TARGETS.get(terrain, 300)
    
    for week in df['Week'].unique():
        week_df = df[df['Week'] == week]
        
        # Calculate planned vertical (simplified - assume 300m/hr for hill sessions)
        hill_sessions = week_df[week_df['Session'].str.contains('Hill|Threshold', na=False)]
        total_vert = len(hill_sessions) * 300  # Rough estimate
        
        # Calculate target based on weekly hours
        total_hours = week_df['Duration'].str.extract('(\d+)').astype(float).sum()
        target_vert = target_vert_per_hour * total_hours
        
        # If under 90% of target, convert easy runs to Roche treadmill
        if total_vert < 0.9 * target_vert:
            easy_runs = week_df[week_df['Session'] == 'Easy Run']
            if not easy_runs.empty:
                # Convert first easy run to Roche treadmill
                first_easy_idx = easy_runs.index[0]
                df.loc[first_easy_idx, 'Session'] = 'Roche Treadmill'
                df.loc[first_easy_idx, 'Description'] = '4mph, increase incline to VT1 HR'
    
    return df

def _schedule_hwi(df: pd.DataFrame, is_race_build: bool = False, is_evergreen_with_heat: bool = False) -> pd.DataFrame:
    """Add heat training schedule"""
    if df.empty:
        return df
        
    df = df.copy()
    df['HWI'] = ""
    
    # Find day type column
    day_type_col = None
    for col in ['Day_Type', 'Type', 'Session_Type']:
        if col in df.columns:
            day_type_col = col
            break
    
    if is_evergreen_with_heat:
        # Loading phase: first 10 days, 30min daily (skip shift days)
        loading_days = df.head(10)
        for idx in loading_days.index:
            if day_type_col and 'Shift' not in str(df.loc[idx, day_type_col]):
                df.loc[idx, 'HWI'] = "30min @40°C"
            elif day_type_col is None:
                df.loc[idx, 'HWI'] = "30min @40°C"
        
        # Maintenance: 3x/week, 25min
        remaining_days = df.iloc[10:]
        hwi_pattern = [True, False, True, False, True, False, False]  # M-W-F pattern
        pattern_idx = 0
        for idx in remaining_days.index:
            if day_type_col and 'Shift' not in str(df.loc[idx, day_type_col]) and hwi_pattern[pattern_idx % 7]:
                df.loc[idx, 'HWI'] = "25min @38°C"
            elif day_type_col is None and hwi_pattern[pattern_idx % 7]:
                df.loc[idx, 'HWI'] = "25min @38°C"
            pattern_idx += 1
            
    elif is_race_build:
        total_weeks = df['Week'].max()
        
        for week in df['Week'].unique():
            week_df = df[df['Week'] == week]
            
            if week <= 2:  # Loading phase
                # Daily 30min (skip shift days)
                for idx in week_df.index:
                    if day_type_col and 'Shift' not in str(df.loc[idx, day_type_col]):
                        df.loc[idx, 'HWI'] = "30min @40°C"
                    elif day_type_col is None:
                        df.loc[idx, 'HWI'] = "30min @40°C"
                        
            elif week <= total_weeks - 2:  # Maintenance
                # 3x/week 25min
                hwi_days = week_df.head(3)  # First 3 non-shift days
                for idx in hwi_days.index:
                    if day_type_col and 'Shift' not in str(df.loc[idx, day_type_col]):
                        df.loc[idx, 'HWI'] = "25min @38°C"
                    elif day_type_col is None:
                        df.loc[idx, 'HWI'] = "25min @38°C"
                        
            else:  # Taper
                # 2x/week 20min
                hwi_days = week_df.head(2)
                for idx in hwi_days.index:
                    if day_type_col and 'Shift' not in str(df.loc[idx, day_type_col]):
                        df.loc[idx, 'HWI'] = "20min @38°C"
                    elif day_type_col is None:
                        df.loc[idx, 'HWI'] = "20min @38°C"
    
    return df

def _add_wucd_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add warm-up and cool-down columns"""
    if df.empty:
        return df
        
    df = df.copy()
    wu_cd_data = [_split_wucd(session) for session in df['Session']]
    df['WU'] = [item[0] for item in wu_cd_data]
    df['CD'] = [item[1] for item in wu_cd_data]
    return df

def _format_duration(duration_str: str) -> str:
    """Convert duration to h:mm format if >60 minutes"""
    if not duration_str or not duration_str.replace('min', '').isdigit():
        return duration_str
        
    minutes = int(duration_str.replace('min', ''))
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}:{mins:02d}"
    return duration_str

# ───────────────────────── Streamlit UI ─────────────────────────
with st.sidebar:
    st.header("Configure Variables")
    
    # Basic inputs with numeric boxes alongside sliders
    start_date = st.date_input("Start Date", dt.date.today())
    
    col1, col2 = st.columns([3, 1])
    with col1:
        hrmax = st.slider("Max HR (HRmax)", 100, 230, 183)
    with col2:
        hrmax = st.number_input("", value=hrmax, min_value=100, max_value=230, key="hrmax_num")
    
    # VT1 with tooltip
    col1, col2 = st.columns([3, 1])
    with col1:
        vt1 = st.slider("VT1", 80, 200, 150, help="ℹ️ First ventilatory threshold - see Variables & Guidance tab for testing protocol")
    with col2:
        vt1 = st.number_input("", value=vt1, min_value=80, max_value=200, key="vt1_num")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        vo2max = st.slider("VO₂max", 0.0, 90.0, 57.0, step=0.1)
    with col2:
        vo2max = st.number_input("", value=vo2max, min_value=0.0, max_value=90.0, step=0.1, key="vo2_num")

    # Single hours input instead of range
    weekly_hours = st.number_input("Weekly Hours", min_value=1, max_value=25, value=10, step=1)
    weekly_hours_str = str(weekly_hours)

    include_base_block = st.checkbox("Include Base Block", True)
    firefighter_schedule = st.checkbox("Firefighter Schedule", True)
    treadmill_available = st.checkbox("Treadmill Available", firefighter_schedule)  # Default true for firefighters
    terrain_type = st.selectbox("Terrain Type", TERRAIN_OPTIONS, index=2)
    
    # Heat training toggle
    add_heat = st.checkbox("Add Heat Training (HWI)")
    if add_heat:
        st.caption("Loading phase (10-14 days) → Maintenance → Taper. Skips shift days.")
    
    shift_offset = st.number_input("Shift Cycle Offset", 0, 7, 0)

    # Race build section
    add_race = st.checkbox("Add Race Build (optional)")
    if add_race:
        race_date = st.date_input("Race Date", dt.date.today() + dt.timedelta(days=70))
        
        # Race distance slider only appears when race build selected
        col1, col2 = st.columns([3, 1])
        with col1:
            race_distance = st.slider("Race Distance (km)", 5, 150, 50)
        with col2:
            race_distance = st.number_input("", value=race_distance, min_value=5, max_value=1000, key="race_dist_num")
            
        elevation_gain = st.number_input("Elevation Gain (m)", 0, 20000, 2500, step=100)
        
        # Show recommended hours
        g_key = _suggest_key(race_distance)
        rec_hours = DISTANCE_SUGGEST[g_key]
        st.markdown(f"**Recommended for {g_key}: {rec_hours} h/week**")
    else:
        race_date = race_distance = elevation_gain = None

    generate_button = st.button("Generate Plan", type="primary")

# ───────────────────────── Main Generation ─────────────────────────
if generate_button:
    with st.spinner("Generating training plan..."):
        try:
            # Generate base plans
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
            
            # Post-process evergreen plan
            if not comp_df.empty:
                comp_df = _add_wucd_columns(comp_df)
                comp_df = _insert_downhill(comp_df, is_race_build=False)
                comp_df = _apply_roche(comp_df, terrain_type, treadmill_available)
                if add_heat:
                    comp_df = _schedule_hwi(comp_df, is_evergreen_with_heat=True)
                
                # Format durations
                if 'Duration' in comp_df.columns:
                    comp_df['Duration'] = comp_df['Duration'].apply(_format_duration)
                
                # Add block focus column
                total_weeks = comp_df['Week'].max() if 'Week' in comp_df.columns else 12
                if 'Week' in comp_df.columns:
                    comp_df['Block Focus'] = comp_df['Week'].apply(
                        lambda w: "Base/Economy" if w <= total_weeks//3 
                        else "Threshold/VO₂" if w <= 2*total_weeks//3 
                        else "Speed-Endurance"
                    )

            # Post-process race plan
            if add_race and not race_df.empty:
                race_df = _add_wucd_columns(race_df)
                race_df = _insert_downhill(race_df, is_race_build=True)
                race_df = _apply_roche(race_df, terrain_type, treadmill_available)
                if add_heat:
                    race_df = _schedule_hwi(race_df, is_race_build=True)
                
                # Format durations
                if 'Duration' in race_df.columns:
                    race_df['Duration'] = race_df['Duration'].apply(_format_duration)
                
                # Add block focus with taper
                total_weeks = race_df['Week'].max() if 'Week' in race_df.columns else 8
                if 'Week' in race_df.columns:
                    race_df['Block Focus'] = race_df['Week'].apply(
                        lambda w: "Base/Economy" if w <= total_weeks//3
                        else "Threshold/VO₂" if w <= 2*total_weeks//3
                        else "Taper" if w > total_weeks - 2
                        else "Speed-Endurance"
                    )
                    
        except Exception as e:
            st.error(f"Error generating plan: {str(e)}")
            st.error("Please check that generate_training_plan_v4.py is working correctly.")
            comp_df = pd.DataFrame()
            race_df = pd.DataFrame()

    # ───────────────────────── Tabs Display ─────────────────────────
    tabs = st.tabs(["Evergreen Plan", "Race Plan", "Variables & Guidance", "Info & References"])

    with tabs[0]:
        st.subheader("12-Week Evergreen Training Block")
        if not comp_df.empty:
            st.dataframe(comp_df, use_container_width=True, height=600)
        else:
            st.error("No evergreen plan generated")

    with tabs[1]:
        st.subheader("Race-Specific Training Block")
        if add_race and not race_df.empty:
            st.dataframe(race_df, use_container_width=True, height=600)
        else:
            st.info("Race build not generated (add race details in sidebar)")

    with tabs[2]:
        st.subheader("Variables & Guidance")
        
        # Variable summary table
        vars_df = pd.DataFrame({
            "Variable": ["Start Date", "Weekly Hours", "Terrain", "Base Block", "Firefighter", "Treadmill", "Heat Training", "Shift Offset"],
            "Value": [start_date, weekly_hours_str, terrain_type, include_base_block, firefighter_schedule, treadmill_available, add_heat, shift_offset]
        })
        if add_race:
            race_vars = pd.DataFrame({
                "Variable": ["Race Date", "Race Distance (km)", "Elevation Gain (m)"],
                "Value": [race_date, race_distance, elevation_gain]
            })
            vars_df = pd.concat([vars_df, race_vars], ignore_index=True)
        
        st.table(vars_df)
        
        # Weekly hours guidance
        st.subheader("Weekly Hours Guidance")
        hours_df = pd.DataFrame({
            "Race Distance": list(DISTANCE_SUGGEST.keys()),
            "Recommended Hours/Week": list(DISTANCE_SUGGEST.values())
        })
        st.table(hours_df)
        
        # Fuel & hydration guidance  
        st.subheader("Fuel & Hydration Guidance")
        st.table(FUEL_TABLE)
        st.caption("*Adjust upward for heat, altitude, or individual needs. Start fueling early in longer efforts.*")
        
        # Exercise glossary
        st.subheader("Exercise Glossary")
        with st.expander("Click to expand full exercise descriptions"):
            for name, description in GLOSSARY.items():
                st.markdown(f"**{name}**")
                st.markdown(description)
                st.markdown("---")

    with tabs[3]:
        st.subheader("Info & References")
        
        st.markdown("### Block & Taper Rationale")
        st.markdown("*Base/Economy → Threshold/VO₂ → Speed-Endurance → 2-week exponential taper.*")
        st.markdown("""
        The periodization follows classic linear progression: aerobic base development, 
        lactate threshold and VO₂max improvement, then neuromuscular power and speed-endurance. 
        The 2-week taper reduces volume by 40-60% while maintaining intensity to optimize 
        performance while minimizing fatigue.
        """)
        
        st.markdown("### Shift-Cycle Explanation")
        st.markdown("""
        The 48/96 firefighter schedule creates a predictable pattern: 2 days on, 4 days off. 
        The shift offset aligns your long runs and key workouts with off-days when you're 
        fresh and have adequate recovery time. This maximizes training adaptation while 
        managing occupational stress.
        """)
        
        st.markdown("### Heat-Training Background") 
        st.markdown("""
        Heat acclimation improves performance through increased plasma volume, improved 
        cardiovascular efficiency, and enhanced thermoregulation. The protocol uses 
        post-exercise hot water immersion (HWI) following Patterson et al. 2021:
        
        - **Loading**: 10-14 days of 30min @40°C daily (skip shift days)
        - **Maintenance**: 3×/week 20-25min @≥38°C to preserve adaptations  
        - **Taper**: Reduce to 2×/week 15-20min to minimize additional stress
        """)
        
        st.markdown("### Vertical Gain Targets")
        st.markdown("Weekly vertical gain targets by terrain type:")
        vert_df = pd.DataFrame({
            "Terrain": list(VERT_TARGETS.keys()),
            "Target (m/hour)": list(VERT_TARGETS.values())
        })
        st.table(vert_df)
        
        st.markdown("### References")
        st.markdown("""
        **Training Periodization & Tapering:**
        - Bosquet L, Mujika I. *Sports Med* 2012
        - Mujika I, Padilla S. *Int J Sports Med* 2003
        - Soligard T et al. *BJSM* 2016
        
        **Heat Acclimation:**
        - Patterson MJ et al. *Scand J Med Sci Sports* 2021
        - Casadio JR et al. *Front Physiol* 2024
        - Scoon GSM et al. *J Sci Med Sport* 2007
        
        **Downhill Running & RBE:**
        - Chen TC et al. *Eur J Appl Physiol* 2023
        - Hoffman MD et al. *Int J Sports Physiol Perf* 2014
        - Millet GY et al. *Sports Med* 2019
        
        **Strength & Plyometrics:**
        - Balsalobre-Fernández C et al. *J Strength Cond Res* 2020
        - Duarte J et al. *Sports Med* 2022
        - Beattie K et al. *Sports Med* 2017
        
        **Fuel & Hydration:**
        - Jeukendrup A. *Sports Sci Exchange* 2024
        - Burke LM et al. *J Sports Sci* 2019
        - Cheuvront SN, Kenefick RW. *Am J Clin Nutr* 2014
        
        **Trail Running Performance:**
        - Scheer V, Vilalta-Franch J. *Int J Sports Physiol Perf* 2021
        - Hoffman MD, Wegelin JA. *PLoS One* 2009
        - Millet GY, Millet GP. *Sports Med* 2012
        """)

    # ───────────────────────── Downloads ─────────────────────────
    st.subheader("Downloads")
    
    # Prepare variables dictionary for Excel export
    vars_dict = {
        "Start Date": str(start_date),
        "HRmax": hrmax,
        "VT1": vt1,
        "VO2max": vo2max,
        "Weekly Hours": weekly_hours_str,
        "Terrain": terrain_type,
        "Base Block": include_base_block,
        "Firefighter": firefighter_schedule,
        "Treadmill": treadmill_available,
        "Heat Training": add_heat,
        "Shift Offset": shift_offset,
    }
    
    if add_race:
        vars_dict.update({
            "Race Date": str(race_date),
            "Race Distance (km)": race_distance,
            "Elevation Gain (m)": elevation_gain,
        })
    
    # In-memory XLSX download
    if not comp_df.empty:
        buffer = BytesIO()
        try:
            # Use existing save function with buffer
            save_plan_to_excel(comp_df, race_df if add_race else pd.DataFrame(), vars_dict, buffer)
            buffer.seek(0)
            
            st.download_button(
                label="📊 Download Complete Plan (XLSX)",
                data=buffer,
                file_name=f"trail_plan_{start_date.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.warning(f"XLSX export failed: {e}. Using CSV fallback.")
    
    # CSV downloads
    col1, col2 = st.columns(2)
    
    with col1:
        if not comp_df.empty:
            st.download_button(
                label="📄 Download Evergreen Plan (CSV)",
                data=comp_df.to_csv(index=False).encode('utf-8'),
                file_name=f"evergreen_plan_{start_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if add_race and not race_df.empty:
            st.download_button(
                label="📄 Download Race Plan (CSV)", 
                data=race_df.to_csv(index=False).encode('utf-8'),
                file_name=f"race_plan_{start_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

else:
    st.info("👈 Configure your training parameters in the sidebar and click 'Generate Plan' to begin.")