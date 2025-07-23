import os
import csv
import math
import glob
import re
import time
import h5py
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from datetime import datetime
import notebook_utilities as nu
import tqdm

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Base directory containing simulation folders
root_dir = "/ocean/projects/ees250010p/shared/02_simulations/scenarios/"
scenario_name = "erdc_baseline"

base_dir = f"{root_dir}/{scenario_name}"
output_csv = f"{scenario_name}_simulation_summary_updated.csv"
slurm_log_dir = f"{root_dir}/_logs/erdc_baseline/slurmout"

headers = [
    "Directory", "Status", "Duration", "SUs", "Failure Reason",
    "Vol Error (AF)", "Vol Error (%)", "Max WSEL Err",
    "Start Time", "End Time", "Failure Info",
    "Max WSE", "Max Depth", "Max Velocity", "Max Volume", "Max Flow Balance",
    "Max Wind", "Mean BC", "Max BC"
]

rows = []
success_count = 0
failure_count = 0
running_count = 0
total_su = 0  # Track total SUs only for successful runs

def format_time(raw_time):
    try:
        parts = raw_time.strip().split()
        if len(parts) == 6:
            raw_time = " ".join(parts[:4] + [parts[5]])  # Drop timezone
        dt = datetime.strptime(raw_time, "%a %b %d %H:%M:%S %Y")
        return dt.strftime("%b %d %H:%M")
    except:
        return raw_time

def duration_to_hours(duration_str):
    if duration_str == "N/A":
        return 0.0
    match = re.match(r'(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?', duration_str)
    if match:
        h, m, s = match.groups()
        h = int(h) if h else 0
        m = int(m) if m else 0
        s = int(s) if s else 0
        return h + m / 60 + s / 3600
    return 0.0

def infer_status(log_lines, start_time, end_time):
    for line in log_lines:
        if "Finished Unsteady Flow Simulation" in line:
            return "Success"
        elif "Beginning Unsteady Flow Simulation" in line:
            return "Running"
    if start_time != "N/A" and end_time == "N/A":
        return "Running"
    return "Failed"

print(f'Last Updated: {time.ctime()}')

epsg_code_default = 6438
model1_name = 'COJ'

for folder in tqdm.tqdm(sorted(os.listdir(base_dir)[::5]),desc='Processing simulation folders'):
    folder_path = os.path.join(base_dir, folder)
    if not os.path.isdir(folder_path):
        continue

    log_file = os.path.join(folder_path, f"log_{folder}.txt")
    time_file = os.path.join(folder_path, "time_log.txt")
    plan1_dir = os.path.join(folder_path, 'COJCOMPOUNDCOMPUTET.p01.tmp.hdf')

    status = "Unknown"
    duration = "N/A"
    vol_error_af = "N/A"
    vol_error_pct = "N/A"
    max_wsel_err = "N/A"
    start_time = "N/A"
    end_time = "N/A"
    failure_info = ""
    failure_reason = ""
    su = 0
    log_lines = []

    max_wse = max_depth = max_vel = max_vol = max_flow = max_wind = mean_bc = max_bc = "N/A"

    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
            for line in log_lines:
                if "Overall Volume Accounting Error in Acre Feet" in line:
                    vol_error_af = line.split(":")[-1].strip()
                if "Overall Volume Accounting Error as percentage" in line:
                    vol_error_pct = line.split(":")[-1].strip()
                if "The maximum cell wsel error was" in line:
                    max_wsel_err = line.split("was")[-1].strip()
            for line in log_lines[-30:]:
                if "Killed" in line or "error" in line.lower():
                    failure_info += line.strip() + " "

    if os.path.exists(time_file):
        with open(time_file, 'r') as f:
            for line in f:
                if "Model start time" in line:
                    raw = line.split(":", 1)[-1].strip()
                    start_time = format_time(raw)
                elif "Model end time" in line:
                    raw = line.split(":", 1)[-1].strip()
                    end_time = format_time(raw)
                elif "Model duration" in line:
                    duration = line.split(":", 1)[-1].strip()

    status = infer_status(log_lines, start_time, end_time)

    if status == "Success":
        success_count += 1
        failure_info = ""
        failure_reason = ""
        hours = duration_to_hours(duration)
        rounded_hours = math.ceil(hours)
        su = rounded_hours * 3
        total_su += su
    elif status == "Running":
        running_count += 1
    else:
        failure_count += 1
        slurm_log_pattern = os.path.join(slurm_log_dir, f"*_{folder}_run.log")
        matched_logs = glob.glob(slurm_log_pattern)
        if matched_logs:
            with open(matched_logs[0], 'r') as f:
                slurm_content = f.read()
                if "Out Of Memory" in slurm_content or "oom-kill" in slurm_content:
                    failure_reason = "Out of Memory"
                elif "CANCELLED" in slurm_content and "DUE TO TIME LIMIT" in slurm_content:
                    failure_reason = "Time limit reached"

    try:
        data1 = nu.load_data(plan1_dir)
        mdl_name1 = nu.get_model_info(data1)
        available_results = nu.list_hdf_result_fields(data1, mdl_name1)

        df_wse = nu.extract_result_field(data1, mdl_name1, 'Water Surface')
        fdepth = df_wse - df_wse.iloc[0]
        max_wse = round(df_wse.max().max(), 2)
        max_depth = round(fdepth.max().max(), 2)

        if 'Cell Velocity - Velocity X' in available_results:
            df_velx = nu.extract_result_field(data1, mdl_name1, 'Cell Velocity - Velocity X')
            df_vely = nu.extract_result_field(data1, mdl_name1, 'Cell Velocity - Velocity Y')
            df_vel = np.sqrt(df_velx**2 + df_vely**2)
            max_vel = round(df_vel.max().max(), 2)

        if 'Cell Volume' in available_results:
            df_vol = nu.extract_result_field(data1, mdl_name1, 'Cell Volume')
            max_vol = round(df_vol.max().max(), 2)

        if 'Cell Flow Balance' in available_results:
            df_flow = nu.extract_result_field(data1, mdl_name1, 'Cell Flow Balance')
            max_flow = round(df_flow.max().max(), 2)

        #_, _, windx, windy = nu.extract_event_field(data1, 'Wind')
        #df_wind = np.sqrt(windx**2 + windy**2)
        #max_wind = round(np.nanmax(df_wind), 2)
        max_wind = np.nan

        _, bc = nu.extract_event_field(data1, 'Boundary Conditions')
        bc[bc < -100] = np.nan
        mean_bc = round(np.nanmean(bc), 2)
        max_bc = round(np.nanmax(bc), 2)

    except Exception as e:
        print(f"Error processing HDF for {folder}: {e}")

    clean_failure_info = " ".join(failure_info.strip().split())

    rows.append([
        folder, status, duration, su, failure_reason,
        vol_error_af, vol_error_pct, max_wsel_err,
        start_time, end_time, clean_failure_info,
        max_wse, max_depth, max_vel, max_vol, max_flow,
        max_wind, mean_bc, max_bc
    ])

# Write to CSV
with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)

print(f"Summary written to {output_csv}")


