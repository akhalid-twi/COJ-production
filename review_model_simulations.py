import os
import csv
import re
import math
import glob
from datetime import datetime

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Base directory containing simulation folders
root_dir = "/ocean/projects/ees250010p/shared/02_simulations/scenarios/"
scenario_name = "erdc_baseline"

base_dir = f"{root_dir}/{scenario_name}"
output_csv = f"{scenario_name}_simulation_summary.csv"
slurm_log_dir = "{root_dir}/_logs/erdc_baseline/slurmout"

headers = [
    "Directory", "Status", "Duration", "SUs", "Failure Reason",
    "Vol Error (AF)", "Vol Error (%)", "Max WSEL Err",
    "Start Time", "End Time", "Failure Info"
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

for folder in sorted(os.listdir(base_dir)):
    folder_path = os.path.join(base_dir, folder)
    if not os.path.isdir(folder_path):
        continue

    log_file = os.path.join(folder_path, f"log_{folder}.txt")
    time_file = os.path.join(folder_path, "time_log.txt")

    status = "Unknown"
    duration = "N/A"
    vol_error_af = "N/A"
    vol_error_pct = "N/A"
    max_wsel_err = "N/A"
    start_time = "N/A"
    end_time = "N/A"
    failure_info = ""
    failure_reason = ""
    su = 0  # Default SU
    log_lines = []
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
        # Check SLURM log for failure reason
        slurm_log_pattern = os.path.join(slurm_log_dir, f"*_{folder}_run.log")
        matched_logs = glob.glob(slurm_log_pattern)
        if matched_logs:
            with open(matched_logs[0], 'r') as f:
                slurm_content = f.read()
                if "Out Of Memory" in slurm_content or "oom-kill" in slurm_content:
                    failure_reason = "Out of Memory"
                elif "CANCELLED" in slurm_content and "DUE TO TIME LIMIT" in slurm_content:
                    failure_reason = "Time limit reached"

    clean_failure_info = " ".join(failure_info.strip().split())

    rows.append([
        folder, status, duration, su, failure_reason,
        vol_error_af, vol_error_pct, max_wsel_err,
        start_time, end_time, clean_failure_info
    ])

# Write to CSV
with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)

# Print table header
print(f"{'Directory':<15} {'Status':<10} {'Duration':<12} {'SUs':<5} {'Failure Reason':<20} {'Vol Error (AF)':<15} {'Vol Error (%)':<15} {'Max WSEL Err':<15} {'Start Time':<15} {'End Time':<15} {'Failure Info'}")

# Print each row with truncated failure info
for row in rows:
    color = GREEN if row[1] == "Success" else RED if row[1] == "Failed" else YELLOW
    truncated_info = (row[10][:60] + '...') if len(row[10]) > 63 else row[10]
    print(f"{color}{row[0]:<15} {row[1]:<10} {row[2]:<12} {row[3]:<5} {row[4]:<20} {row[5]:<15} {row[6]:<15} {row[7]:<15} {row[8]:<15} {row[9]:<15} {truncated_info}{RESET}")

# Print summary
print("\n" + "="*50)
print("Summary:")
print(f"Total models run: {len(rows)}")
print(f"{GREEN}Successful: {success_count}{RESET}")
print(f"{YELLOW}Running: {running_count}{RESET}")
print(f"{RED}Failed: {failure_count}{RESET}")
print(f"Total SUs used; 4 cpus per task, 8GB min required (successful only): {total_su}")
print("="*50)

