import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
import datetime
import os

# Load the CSV file
csv_file = "erdc_baseline_simulation_summary_updated.csv"
df = pd.read_csv(csv_file)

# Rename columns to match expected names in the dashboard
df.columns = [
    "Directory", "Status", "Duration", "SUs", "Failure Reason", "Vol Error (AF)", "Vol Error (%)", "Max WSEL Err",
    "Start Time", "End Time", "Failure Info", "Max WSE", "Max Depth", "Max Velocity", "Max Volume",
    "Max Flow Balance", "Max Wind", "Mean BC", "Max BC"
]

# Define a function to apply row-wise styling
def highlight_status(row):
    color = ''
    if row['Status'] == 'Success':
        color = 'background-color: lightgreen'
    elif row['Status'] == 'Failed':
        color = 'background-color: lightcoral'
    elif row['Status'] == 'Running':
        color = 'background-color: lightyellow'
    return [color] * len(row)

# Get the last modified time of the file
modified_timestamp = os.path.getmtime(csv_file)
modified_datetime = datetime.datetime.fromtimestamp(modified_timestamp)
current_datetime = datetime.datetime.now()
file_age = current_datetime - modified_datetime

# Streamlit app title
st.title("COJ Production Dashboard")
st.subheader(f" Scenario: ERDC Baseline Conditions")
st.markdown(f"Last updated: {str(modified_datetime)[:-6]}")

total_simulations = 505
completed_simulations = len(df)
st.subheader(f"Simulation Count: {completed_simulations}/{total_simulations}")

progress_percent = int((completed_simulations / total_simulations) * 100)
progress_text = f"Processing simulations... {progress_percent}% complete"
my_bar = st.progress(progress_percent, text=progress_text)

# Optional: Add a status message
if progress_percent < 25:
    st.info("🚧 Just getting started...")
elif progress_percent < 75:
    st.warning("🔄 In progress...")
else:
    st.success("✅ Almost done!")

# Filter simulations by status
success_df = df[df["Status"] == "Success"].copy()
failed_df = df[df["Status"] == "Failed"].copy()
running_df = df[df["Status"] == "Running"].copy()

# Convert SUs to numeric
success_df["SUs"] = pd.to_numeric(success_df["SUs"], errors='coerce')
total_sus = success_df["SUs"].sum()

# Hydrodynamic and forcing plots
st.subheader("Hydrodynamic Model Outputs and Forcings")

# Convert relevant columns to numeric
for col in ["Max WSE", "Max Depth", "Max Velocity", "Max Volume", "Max Flow Balance", "Max Wind", "Mean BC", "Max BC"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Plot each metric if available
metrics = {
    "Max WSE": "Maximum Water Surface Elevation",
    "Max Depth": "Maximum Flood Depth",
    "Max Velocity": "Maximum Velocity",
    "Max Volume": "Maximum Volume",
    "Max Flow Balance": "Maximum Flow Balance",
    "Max Wind": "Maximum Wind Speed",
    "Mean BC": "Mean Downstream Boundary Condition",
    "Max BC": "Maximum Downstream Boundary Condition"
}

for col, title in metrics.items():
    if col in df.columns:
        fig = px.bar(df, x="Directory", y=col, title=title)
        st.plotly_chart(fig, use_container_width=True)

# SU usage plot
st.subheader("Service Units (SUs) Used per Successful Simulation")
st.markdown(f"**Total SUs Used:** {total_sus:,}")
fig_su = px.bar(success_df, x="Directory", y="SUs", color="SUs", title="SUs per Successful Run")
st.plotly_chart(fig_su, use_container_width=True)

# Status table
styled_df = df.style.apply(highlight_status, axis=1)
st.subheader("Status Table")
st.dataframe(styled_df, use_container_width=True)

# Simulated counts
completed_count = len(success_df) + len(failed_df)
running_count = len(running_df)
failed_count = len(failed_df)
successful_count = len(success_df)

# Horizontal stacked bar: Completed vs Running
st.subheader("Completed vs Running Simulations (Stacked)")
fig_completion = go.Figure()
fig_completion.add_trace(go.Bar(
    y=["Simulations"],
    x=[completed_count],
    name="Completed",
    orientation='h',
    marker=dict(color='lightgreen')
))
fig_completion.add_trace(go.Bar(
    y=["Simulations"],
    x=[running_count],
    name="Running",
    orientation='h',
    marker=dict(color='lightyellow')
))
fig_completion.update_layout(
    barmode='stack',
    xaxis_title="Count",
    height=300
)
st.plotly_chart(fig_completion, use_container_width=True)

# Horizontal stacked bar: Failed vs Successful
st.subheader("Failed vs Successful Simulations (Stacked)")
fig_fail_success = go.Figure()
fig_fail_success.add_trace(go.Bar(
    y=["Simulations"],
    x=[failed_count],
    name="Failed",
    orientation='h',
    marker=dict(color='lightcoral')
))
fig_fail_success.add_trace(go.Bar(
    y=["Simulations"],
    x=[successful_count],
    name="Successful",
    orientation='h',
    marker=dict(color='lightgreen')
))
fig_fail_success.update_layout(
    barmode='stack',
    xaxis_title="Count",
    height=300
)
st.plotly_chart(fig_fail_success, use_container_width=True)

# Pie chart of success vs failure
status_counts = df["Status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]
color_map = {
    "Success": "lightgreen",
    "Failed": "lightcoral",
    "Running": "lightyellow"
}
fig_pie = px.pie(
    status_counts,
    names="Status",
    values="Count",
    title="Failure vs Success Distribution",
    color="Status",
    color_discrete_map=color_map
)
st.subheader("Simulation Status Distribution")
st.plotly_chart(fig_pie, use_container_width=True)


