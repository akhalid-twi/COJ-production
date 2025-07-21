#!/bin/bash

# Run the Python script to get the status update
python review_model_simulations.py

# Get the current date and time
datetime=$(date +"%m/%d @ %I:%M%p")

# Upload the new CSV with a dynamic commit message
git add erdc_baseline_simulation_summary.csv
git commit -m "updated production log $datetime"
git push

