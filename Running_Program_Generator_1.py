import pandas as pd
import os
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from datetime import datetime, timedelta

# Function to generate training plan based on user inputs
def generate_training_plan(training_phase, event_focus, weeks_to_peak, start_date, max_hr):
    # Define basic structure of a training week with more variety
    week_plan = {
        "Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "Workout Type": ["Rest", "Run", "Quality Run 1", "Run", "Quality Run 2", "Long Run", "Active Recovery"],
        "Duration (mins)": [0, 60, 75, 60, 75, 150, 45],
        "HR Zone": ["-", "Zone 2", "Zone 4", "Zone 2", "Zone 4", "Zone 2", "Zone 1"],
        "Notes": [
            "Rest day", 
            "Easy run", 
            "Threshold intervals: 5 x 5 min @ Zone 4 with 2 min recovery", 
            "Easy recovery run", 
            "Hill repeats: 8 x 90 sec uphill @ Zone 4, easy jog down recovery", 
            "Long endurance run", 
            "Light effort"
        ],
    }

    # Calculate heart rate ranges based on max HR for each zone (Jack Daniels' guidelines)
    hr_zones = {
        "Zone 1": (0.6 * max_hr, 0.72 * max_hr),
        "Zone 2": (0.72 * max_hr, 0.82 * max_hr),
        "Zone 3": (0.82 * max_hr, 0.88 * max_hr),
        "Zone 4": (0.88 * max_hr, 0.95 * max_hr),
        "Zone 5": (0.95 * max_hr, 1.0 * max_hr)
    }

    # Create a DataFrame for a week
    week_df = pd.DataFrame(week_plan)

    # Determine number of weeks for the plan
    if training_phase == "Maintenance":
        weeks_to_peak = 24  # Set maintenance period to 24 weeks

    # Create a DataFrame for the entire plan
    training_plan = pd.concat([week_df] * weeks_to_peak, keys=range(1, weeks_to_peak + 1)).reset_index()
    training_plan.rename(columns={"level_0": "Week", "level_1": "Day Index"}, inplace=True)

    # Adjust Day Index to start from 1 instead of 0
    training_plan["Day Index"] = training_plan["Day Index"] + 1

    # Add Date column based on start date
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    training_plan["Date"] = training_plan.apply(lambda row: (start_date + timedelta(weeks=row["Week"], days=row["Day Index"] - 1)).strftime('%Y-%m-%d'), axis=1)

    # Add HR Range column based on HR Zone
    def get_hr_range(zone):
        if zone in hr_zones:
            return f"{int(hr_zones[zone][0])}-{int(hr_zones[zone][1])} bpm"
        elif "-" in zone:  # Handle multi-zone cases like "Zone 2-4"
            zones = zone.split('-')
            if len(zones) == 2 and zones[0] in hr_zones and zones[1] in hr_zones:
                min_hr = int(hr_zones[zones[0]][0])
                max_hr = int(hr_zones[zones[1]][1])
                return f"{min_hr}-{max_hr} bpm"
        return "-"

    training_plan["HR Range"] = training_plan["HR Zone"].apply(get_hr_range)

    # Add more variety to Quality Runs and Long Runs
    for i, row in training_plan.iterrows():
        if row["Workout Type"] == "Quality Run 1":
            if i % 3 == 0:
                training_plan.at[i, "Notes"] = "Fartlek: 10 x 1 min @ Zone 4 with 1 min recovery"
                training_plan.at[i, "HR Zone"] = "Zone 4"
            elif i % 3 == 1:
                training_plan.at[i, "Notes"] = "Tempo run: 20 min @ Zone 3"
                training_plan.at[i, "HR Zone"] = "Zone 3"
            elif i % 3 == 2:
                training_plan.at[i, "Notes"] = "Threshold intervals: 6 x 4 min @ Zone 4 with 2 min recovery"
                training_plan.at[i, "HR Zone"] = "Zone 4"
        elif row["Workout Type"] == "Quality Run 2":
            if i % 3 == 0:
                training_plan.at[i, "Notes"] = "Hill sprints: 10 x 30 sec @ Zone 5, walk back down recovery"
                training_plan.at[i, "HR Zone"] = "Zone 5"
            elif i % 3 == 1:
                training_plan.at[i, "Notes"] = "Progression run: Start at Zone 2, finish at Zone 4"
                training_plan.at[i, "HR Zone"] = "Zone 2-4"
                training_plan.at[i, "HR Range"] = get_hr_range("Zone 2-4")
                training_plan.at[i, "HR Range"] = get_hr_range("Zone 2-4")
                training_plan.at[i, "HR Zone"] = "Zone 2-4"
            elif i % 3 == 2:
                training_plan.at[i, "Notes"] = "Interval run: 8 x 3 min @ Zone 4 with 90 sec recovery"
                training_plan.at[i, "HR Zone"] = "Zone 4"
        elif row["Workout Type"] == "Long Run" and event_focus == "Ultra":
            if i % 2 == 0:
                training_plan.at[i, "Notes"] = "Back-to-back long runs: Saturday 3 hrs, Sunday 2 hrs @ Zone 2"
                training_plan.at[i, "HR Zone"] = "Zone 2"
            else:
                training_plan.at[i, "Notes"] = "Long run with elevation focus: 3 hrs with steep climbs @ Zone 2"
                training_plan.at[i, "HR Zone"] = "Zone 2"

    # Adjust training plan based on inputs
    if training_phase == "Peaking":
        training_plan.loc[training_plan["Workout Type"] == "Long Run", "Duration (mins)"] += 30  # Increase long run duration for peaking
        if event_focus == "Ultra":
            training_plan.loc[training_plan["Workout Type"] == "Long Run", "Duration (mins)"] += 60  # Additional increase for ultra peaking
            # Replace Quality Runs with ultra-specific workouts
            training_plan.loc[(training_plan["Workout Type"] == "Quality Run 1") & (training_plan["Week"] >= weeks_to_peak - 4), "Notes"] = "Back-to-back long runs: Saturday 3 hrs, Sunday 2 hrs @ Zone 2"
            training_plan.loc[(training_plan["Workout Type"] == "Quality Run 2") & (training_plan["Week"] >= weeks_to_peak - 4), "Notes"] = "Power hiking practice: 60 mins uphill focus @ Zone 2"
            training_plan.loc[(training_plan["Workout Type"] == "Quality Run 1") & (training_plan["Week"] >= weeks_to_peak - 4), "HR Zone"] = "Zone 2"
            training_plan.loc[(training_plan["Workout Type"] == "Quality Run 2") & (training_plan["Week"] >= weeks_to_peak - 4), "HR Zone"] = "Zone 2"
    elif training_phase == "Maintenance":
        # Periodization for maintenance: reduce intensity every 4th week for recovery
        training_plan.loc[training_plan["Week"] % 4 == 0, "Duration (mins)"] *= 0.8  # Reduce workout duration by 20% for recovery weeks

    # Update HR Range column based on new HR Zone assignments
    training_plan["HR Range"] = training_plan["HR Zone"].apply(get_hr_range)

    return training_plan

# Function to validate date format
def validate_date_format(date_text):
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# Function to get user inputs using a GUI with dropdowns
def get_user_inputs():
    root = tk.Tk()
    root.title("Training Plan Input")
    root.geometry("400x400")

    def submit():
        training_phase = training_phase_var.get()
        event_focus = event_focus_var.get()
        start_date = start_date_entry.get()
        weeks_to_peak = weeks_to_peak_var.get()
        max_hr = max_hr_entry.get()

        if not training_phase or not event_focus or not start_date or not max_hr:
            messagebox.showerror("Error", "All fields are required!")
            return

        if not validate_date_format(start_date):
            messagebox.showerror("Error", "Invalid date format! Please enter the date in YYYY-MM-DD format.")
            return

        if training_phase == "Maintenance":
            weeks_to_peak = 24  # Set default for maintenance phase

        root.destroy()
        user_inputs.append((training_phase, event_focus, int(weeks_to_peak), start_date, int(max_hr)))

    training_phase_var = tk.StringVar()
    event_focus_var = tk.StringVar()
    weeks_to_peak_var = tk.StringVar(value="24")

    # Training Phase Dropdown
    tk.Label(root, text="Select Training Phase:").pack(pady=5)
    training_phase_dropdown = ttk.Combobox(root, textvariable=training_phase_var)
    training_phase_dropdown['values'] = ("Maintenance", "Peaking")
    training_phase_dropdown.pack(pady=5)

    # Event Focus Dropdown
    tk.Label(root, text="Select Event Focus:").pack(pady=5)
    event_focus_dropdown = ttk.Combobox(root, textvariable=event_focus_var)
    event_focus_dropdown['values'] = ("Marathon", "Ultra")
    event_focus_dropdown.pack(pady=5)

    # Start Date Entry
    tk.Label(root, text="Enter Start Date (YYYY-MM-DD):").pack(pady=5)
    start_date_entry = tk.Entry(root)
    start_date_entry.pack(pady=5)

    # Weeks to Peak Entry (only for Peaking phase)
    tk.Label(root, text="Enter Number of Weeks to Peak (e.g., 12, 16, 20):").pack(pady=5)
    weeks_to_peak_entry = ttk.Combobox(root, textvariable=weeks_to_peak_var)
    weeks_to_peak_entry['values'] = ("12", "16", "20")
    weeks_to_peak_entry.pack(pady=5)

    # Max Heart Rate Entry
    tk.Label(root, text="Enter Maximum Heart Rate (bpm):").pack(pady=5)
    max_hr_entry = tk.Entry(root)
    max_hr_entry.pack(pady=5)

    # Submit Button
    submit_button = tk.Button(root, text="Submit", command=submit)
    submit_button.pack(pady=20)

    user_inputs = []
    root.mainloop()

    return user_inputs[0]

# Get user inputs
user_inputs = get_user_inputs()
training_phase, event_focus, weeks_to_peak, start_date, max_hr = user_inputs

# Generate the training plan using the user inputs
training_plan = generate_training_plan(training_phase, event_focus, weeks_to_peak, start_date, max_hr)

# Save the training plan to a new Excel file in the specified directory with a readable name
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
unique_file_name = f"E:\Running Program Generator\Training_Plan_{timestamp}.xlsx"
training_plan.to_excel(unique_file_name, index=False)

messagebox.showinfo("Success", f"Training plan saved to {unique_file_name}")
