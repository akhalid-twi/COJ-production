#!/bin/bash

# Run the Python script to get the status update
python get_model_status_info.py

# add a code to check differences in the _full file and the _summary file to add
python update_csv.py

# Get the current date and time
datetime=$(date +"%m/%d @ %I:%M%p")

# Upload the new CSV with a dynamic commit message
git add updated_erdc_baseline_simulation_summary_full.csv
git commit -m "updated production log $datetime"
git push

