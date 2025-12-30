
import os
import csv
import re
import math
import glob
from datetime import datetime

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
MAGENTA = '\033[95m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BLUE = '\033[94m'


# Base directory containing simulation folders
root_dir = "/ocean/projects/ees250010p/shared/02_simulations/scenarios/"
scenario_name = "a_optimal_sample_base"  # Change as needed

base_dir = f"{root_dir}/{scenario_name}"
output_csv = f"{scenario_name}_simulation_basic_summary.csv"
slurm_log_dir = f"/ocean/projects/ees250010p/shared/02_simulations/_logs/{scenario_name}/slurmout"  # FIXED f-string
slurm_log_err_dir = f"{slurm_log_dir}/stdout"


headers = [
    "Directory", "Status", "Duration", "SUs", "Failure Reason",
    "Vol Error (AF)", "Vol Error (%)", "Max WSEL Err",
    "Start Time", "End Time", "Failure Info",
    "Max WSE (ft)", "Max Depth (ft)", "Max Velocity (ft/s)",
    "Max Volume (ft^3)", "Max Flow Balance (ft^3/s)",
    "Max Wind (ft/s)", "Mean BC (ft)", "Max BC (ft)"
]



rows = []
success_count = 0
failure_count = 0
running_count = 0
pending_count = 0
out_of_time_count = 0
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

    # Find log file
    log_file = None
    for filename in os.listdir(folder_path):
        if filename.startswith("log_") and filename.endswith(".txt"):
            log_file = os.path.join(folder_path, filename)


    time_file = os.path.join(folder_path, "time_log.txt")


    # If log file doesn't exist, determine if run is pending, running, or failed initialization
    if not log_file:
        if os.path.exists(time_file):
            status = "Running"
        else:
            status = "Initializing"

            if status == "Initializing":
                pending_count += 1
            else:
                running_count += 1

    
        rows.append([
            folder, status, "N/A", 0, "", "N/A", "N/A", "N/A",
            "N/A", "N/A", ""
        ])
        continue

    status = "Unknown"
    duration = "N/A"
    vol_error_af = "N/A"
    vol_error_pct = "N/A"
    max_wsel_err = "N/A"
    start_time = "N/A"
    end_time = "N/A"

    max_wse = "N/A"
    max_depth = "N/A"
    max_velocity = "N/A"
    max_volume = "N/A"
    max_flow_balance = "N/A"
    max_wind = "N/A"
    mean_bc = "N/A"
    max_bc = "N/A"

    failure_info = ""
    failure_reason = ""
    su = 0  # Default SU
    log_lines = []

    if log_file and os.path.exists(log_file):
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

    # Check SLURM logs for failure reason or time limit
    slurm_log_pattern = os.path.join(slurm_log_dir, f"*_{folder}_run.log")
    
    matched_logs = glob.glob(slurm_log_pattern)
    #print(slurm_log_pattern,matched_logs)

    if matched_logs:
        filename = os.path.basename(matched_logs[0])
        prefix = filename.split(f"_{folder}_run.log")[0]

        slurm_err_file = os.path.join(slurm_log_err_dir, f"output_{prefix}.out")

        # SAFELY handle missing slurm file
        if not os.path.isfile(slurm_err_file):
            slurm_content = ""   # No logfile yet (job pending or running)
        else:
            with open(slurm_err_file, 'r') as f:
                slurm_content = f.read()

        # Process failure cases
        if "Out Of Memory" in slurm_content or "oom-kill" in slurm_content:
            failure_reason = "Out of Memory"
        elif "CANCELLED" in slurm_content and "DUE TO TIME LIMIT" in slurm_content:
            failure_reason = "Time limit reached"
            if status == "Running":
                status = "Incomplete-Slurm timeout"

    # Update counters and compute SUs
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

    elif status == "Initializing":
        pending_count += 1

    elif status == "Out of Time Limit":
        out_of_time_count += 1
    else:
        failure_count += 1

    clean_failure_info = " ".join(failure_info.strip().split())


    rows.append([
        folder, status, duration, su, failure_reason,
        vol_error_af, vol_error_pct, max_wsel_err,
        start_time, end_time, clean_failure_info,
        max_wse, max_depth, max_velocity,
        max_volume, max_flow_balance, max_wind,
        mean_bc, max_bc
    ])

# Write to CSV
with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)

# Print table header
print(f"{'Directory':<15} {'Status':<18} {'Duration':<12} {'SUs':<5} {'Failure Reason':<20} {'Vol Error (AF)':<15} {'Vol Error (%)':<15} {'Max WSEL Err':<15} {'Start Time':<15} {'End Time':<15} {'Failure Info'}")

# Print each row with truncated failure info
for row in rows:

    #color = GREEN if row[1] == "Success" else RED if row[1] in ["Failed", "Incomplete-Slurm timeout"] else YELLOW


    if row[1] == "Success":
        color = GREEN
    elif row[1] == "Failed" or row[1] == "Incomplete-Slurm timeout":
        color = RED
    elif row[1] == "Initializing":
        color = BLUE
    else:
        color = YELLOW  # Running


    truncated_info = (row[10][:60] + '...') if len(row[10]) > 63 else row[10]
    print(f"{color}{row[0]:<15} {row[1]:<18} {row[2]:<12} {row[3]:<5} {row[4]:<20} {row[5]:<15} {row[6]:<15} {row[7]:<15} {row[8]:<15} {row[9]:<15} {truncated_info}{RESET}")

# Print summary
print("\n" + "="*50)
print("Summary:")
print(f"Total models run: {len(rows)}")
print(f"{GREEN}Successful: {success_count}{RESET}")
print(f"{YELLOW}Running: {running_count}{RESET}")
print(f"{BLUE}Initializing: {pending_count}{RESET}")
print(f"{RED}Failed: {failure_count}{RESET}")
print(f"{MAGENTA}Incomplete-Slurm timeout: {out_of_time_count}{RESET}")
print(f"Total SUs used; ~4 to 5 cpus per task, 8GB min required (successful only): {total_su}")
print("="*50)

