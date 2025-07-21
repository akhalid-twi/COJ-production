import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go

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
# st.subheader("Simulation Results Table")
# st.dataframe(df)

# Apply styling
styled_df = df.style.apply(highlight_status, axis=1)

# Display the styled dataframe
st.subheader("Simulation Results Table")
st.dataframe(styled_df)

# Interactive bar chart of SU usage
st.subheader("Service Units (SUs) Used per Successful Simulation")
fig_su = px.bar(success_df, x="Directory", y="SUs", color="SUs", title="SUs per Successful Run")
st.plotly_chart(fig_su)


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
    marker=dict(color='green')
))
fig_completion.add_trace(go.Bar(
    y=["Simulations"],
    x=[running_count],
    name="Running",
    orientation='h',
    marker=dict(color='orange')
))
fig_completion.update_layout(
    barmode='stack',
    xaxis_title="Count",
    height=300
)
st.plotly_chart(fig_completion)

# Horizontal stacked bar: Failed vs Successful
st.subheader("Failed vs Successful Simulations (Stacked)")
fig_fail_success = go.Figure()
fig_fail_success.add_trace(go.Bar(
    y=["Simulations"],
    x=[failed_count],
    name="Failed",
    orientation='h',
    marker=dict(color='red')
))
fig_fail_success.add_trace(go.Bar(
    y=["Simulations"],
    x=[successful_count],
    name="Successful",
    orientation='h',
    marker=dict(color='blue')
))
fig_fail_success.update_layout(
    barmode='stack',
    xaxis_title="Count",
    height=300
)
st.plotly_chart(fig_fail_success)

# Pie chart of success vs failure
st.subheader("Simulation Status Distribution")
status_counts = df["Status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]
fig_pie = px.pie(status_counts, names="Status", values="Count", title=" Failure vs SuccessDistribution")
st.plotly_chart(fig_pie)

