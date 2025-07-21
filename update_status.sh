#!bin/bash


# run to get the status update
python review_model_simulations.py

# upload the new csv
git add erdc_baseline_simulation_summary.csv
git commit -m "updated production log"
git push

# provide login for github


