import os
import subprocess
from pathlib import Path

# Define base paths
base_plan_dir = Path("/ocean/projects/ees250010p/shared/02_simulations/scenarios/erdc_baseline")
output_dir = Path("/ocean/projects/ees250010p/shared/04_analysis/qaqc/erdc_baseline")
output_dir_nb = output_dir / "nb"
output_dir_html = output_dir / "html"

# Create output directories if they don't exist
output_dir_nb.mkdir(parents=True, exist_ok=True)
output_dir_html.mkdir(parents=True, exist_ok=True)

# Get list of storm IDs
storm_ids = [d for d in os.listdir(base_plan_dir) if (base_plan_dir / d).is_dir()]
storm_ids = storm_ids[:50]
#storm_ids = ['S0992']

print(f"Found storm IDs: {storm_ids}")

# List to keep track of failed storm IDs
failed_storms = []

# Loop through each storm ID
for storm_id in storm_ids:
    plan_path = base_plan_dir / storm_id / "COJCOMPOUNDCOMPUTET.p01.tmp.hdf"
    output_notebook = output_dir_nb / f"results_{storm_id}_notebook.ipynb"
    output_html = output_dir_html / f"results_{storm_id}_notebook.html"

    try:
        # Run papermill
        subprocess.run([
            "papermill",
            "review_plan_file.ipynb",
            str(output_notebook),
            "-p", "stormID", storm_id,
            "-p", "plan1_dir", str(plan_path),
            #"--log-output"
        ], check=True)

        # Convert to HTML without code and save in output_dir_html
        subprocess.run([
            "jupyter", "nbconvert",
            "--to", "html",
            "--no-input",
            "--output-dir", str(output_dir_html),
            "--output", f"results_{storm_id}_notebook.html",
            str(output_notebook)
        ], check=True)

    except subprocess.CalledProcessError:
        print(f"❌ Failed to process storm ID: {storm_id}")
        failed_storms.append(storm_id)

# Write failed storm IDs to a text file
failed_file = output_dir / "failed_storms.txt"
with open(failed_file, "w") as f:
    for storm_id in failed_storms:
        f.write(f"{storm_id}\n")

print(f"⚠️ Failed storm IDs: {failed_storms}")
print(f"📄 List written to: {failed_file}")

