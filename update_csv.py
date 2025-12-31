import pandas as pd

scenario = 'erdc_baseline'
scenario = 'a_optimal_sample_base'

# File paths
basic_file = f"{scenario}_simulation_basic_summary.csv"
full_file = f"{scenario}_simulation_summary_full.csv"
output_file = f"updated_{scenario}_simulation_summary_full.csv"

# Load both CSV files
df_basic = pd.read_csv(basic_file)
df_full = pd.read_csv(full_file)

# Identify new rows in basic that are not in full based on 'Directory'
new_rows = df_basic[~df_basic['Directory'].isin(df_full['Directory'])].copy()

# If no new rows, skip appending
if new_rows.empty:
    print("No new rows to append. Files are already in sync.")
    df_full.to_csv(output_file,index=False)
    print(f'Full summary file renamed to updated.')
else:
    # Add missing columns from full to new_rows with NaN values
    for col in df_full.columns:
        if col not in new_rows.columns:
            new_rows[col] = pd.NA

    # Reorder columns to match df_full exactly
    new_rows = new_rows[df_full.columns]

    # Concatenate and save
    df_updated = pd.concat([df_full, new_rows], ignore_index=True)
    df_updated.to_csv(output_file, index=False)

    print(f"Appended {len(new_rows)} new rows. Updated file saved as: {output_file}")


