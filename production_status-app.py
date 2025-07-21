import pandas as pd
import plotly.express as px
import streamlit as st

# Load the CSV file
csv_file = "erdc_baseline_simulation_summary.csv"
df = pd.read_csv(csv_file)

# Streamlit app title
st.title("ERDC Baseline Simulation Dashboard")

# Filter simulations by status
success_df = df[df["Status"] == "Success"].copy()
failed_df = df[df["Status"] == "Failed"].copy()
running_df = df[df["Status"] == "Running"].copy()

# Convert SUs to numeric
success_df["SUs"] = pd.to_numeric(success_df["SUs"], errors='coerce')

# Display the full data table
st.subheader("Simulation Results Table")
st.dataframe(df)

# Horizontally stacked bar chart: Completed vs Running
st.subheader("Simulation Completion Overview")
completed_count = len(success_df) + len(failed_df)
running_count = len(running_df)
completion_data = pd.DataFrame({
    "Status": ["Completed", "Running"],
    "Count": [completed_count, running_count]
})
if completion_data["Count"].sum() > 0:
    fig_completion = px.bar(completion_data, y="Status", x="Count", color="Status",
                            orientation='h', title="Total Simulations: Completed vs Running")
    st.plotly_chart(fig_completion)
else:
    st.info("No data available for Completed vs Running simulations.")

# Horizontally stacked bar chart: Failed vs Successful
st.subheader("Failed vs Successful Simulations")
fail_success_data = pd.DataFrame({
    "Status": ["Failed", "Successful"],
    "Count": [len(failed_df), len(success_df)]
})
if fail_success_data["Count"].sum() > 0:
    fig_fail_success = px.bar(fail_success_data, y="Status", x="Count", color="Status",
                              orientation='h', title="Failed vs Successful Simulations")
    st.plotly_chart(fig_fail_success)
else:
    st.info("No data available for Failed vs Successful simulations.")

