import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# Load the CSV file
csv_file = "erdc_baseline_simulation_summary.csv"
df = pd.read_csv(csv_file)

# Streamlit app title
st.title("ERDC Baseline Simulation Dashboard")

# Filter successful and failed simulations
success_df = df[df["Status"] == "Success"].copy()
failed_df = df[df["Status"] == "Failed"].copy()
running_df = df[df["Status"] == "Running"].copy()

# Convert SUs to numeric
success_df["SUs"] = pd.to_numeric(success_df["SUs"], errors='coerce')


# Display the full data table
st.subheader("Simulation Results Table")
st.dataframe(df)


# Horizontally stacked bar chart: Total vs Running vs Completed
st.subheader("Simulation Completion Overview")
total_count = len(df)
running_count = len(running_df)
completed_count = len(success_df) + len(failed_df)
completion_data = pd.DataFrame({
    "Category": ["Completed", "Running"],
    "Count": [completed_count, running_count]
})
fig_completion = px.bar(completion_data, x="Count", y=["Category"]*2, orientation='h',
                        color="Category", title="Total Simulations: Completed vs Running")
st.plotly_chart(fig_completion)

# Horizontally stacked bar chart: Failed vs Running
st.subheader("Failed vs Running Simulations")
fail_run_data = pd.DataFrame({
    "Category": ["Failed", "Running"],
    "Count": [len(failed_df), len(running_df)]
})
fig_fail_run = px.bar(fail_run_data, x="Count", y=["Category"]*2, orientation='h',
                      color="Category", title="Failed vs Running Simulations")
st.plotly_chart(fig_fail_run)



# Interactive bar chart of SU usage
st.subheader("Service Units (SUs) Used per Successful Simulation")
fig_su = px.bar(success_df, x="Directory", y="SUs", color="SUs", title="SUs per Successful Run")
st.plotly_chart(fig_su)

# Pie chart of success vs failure
st.subheader("Simulation Status Distribution")
status_counts = df["Status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]
fig_pie = px.pie(status_counts, names="Status", values="Count", title="Success vs Failure Distribution")
st.plotly_chart(fig_pie)
