import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
import datetime
import os

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


# Get the last modified time of the file
#try:
modified_timestamp = os.path.getmtime(csv_file)
modified_datetime = datetime.datetime.fromtimestamp(modified_timestamp)
current_datetime = datetime.datetime.now()
file_age = current_datetime - modified_datetime

#print(f"The file '{csv_file}' was last modified on: {modified_datetime}")
#print(f"The file is {file_age.days} days old.")
#except FileNotFoundError:
#    print(f"The file '{csv_file}' does not exist in the current directory.")


# Streamlit app title
st.title("COJ Production Dashboard")
st.subheader(f" Scenario: ERDC Baseline Conditions")


st.markdown(f"Last updated: {str(modified_datetime)[:-6]}")

total_simulations = 505
completed_simulations = len(df) 

st.subheader(f"Total Simulations: {completed_simulations}/{total_simulations}")


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

# Optional: Rerun button
st.button("🔁 Refresh Progress")




# Filter simulations by status
success_df = df[df["Status"] == "Success"].copy()
failed_df = df[df["Status"] == "Failed"].copy()
running_df = df[df["Status"] == "Running"].copy()

# Convert SUs to numeric
success_df["SUs"] = pd.to_numeric(success_df["SUs"], errors='coerce')


total_sus = success_df["SUs"].sum()

# Apply styling
styled_df = df.style.apply(highlight_status, axis=1)

# Display the styled dataframe
st.subheader("Status Table")
st.dataframe(styled_df, use_container_width=True)


# Available Plan to Review

st.subheader("Available QC files to Review")

notebook_url = "https://github.com/akhalid-twi/COJ-production/blob/a6fc0713035084895f43efde2e3915ecd67960e5/example_qc/results_S0155_notebook.ipynb"
download_url = "https://raw.githubusercontent.com/akhalid-twi/COJ-production/a6fc0713035084895f43efde2e3915ecd67960e5/example_qc/results_S0155_notebook.html"

st.markdown(f'<a href="{notebook_url}" target="_blank">🔗 View Notebook for S0155 (code blocks are not hidden)</a>', unsafe_allow_html=True)

st.markdown(
    f'<a href="{download_url}" download target="_blank">⬇️ Download HTML Report for S0155</a>',
    unsafe_allow_html=True
)


# Interactive bar chart of SU usage
st.subheader("Service Units (SUs) Used per Successful Simulation")
st.markdown(f"**Total SUs Used:** {total_sus:,}")
fig_su = px.bar(success_df, x="Directory", y="SUs", color="SUs", title="SUs per Successful Run")
st.plotly_chart(fig_su, use_container_width=True)


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

# Create horizontal stacked bar chart with updated colors
fig_fail_success = go.Figure()
fig_fail_success.add_trace(go.Bar(
    y=["Simulations"],
    x=[failed_count],
    name="Failed",
    orientation='h',
    marker=dict(color='lightcoral')  # Red for Failed
))
fig_fail_success.add_trace(go.Bar(
    y=["Simulations"],
    x=[successful_count],
    name="Successful",
    orientation='h',
    marker=dict(color='lightgreen')  # Green for Successful
))
fig_fail_success.update_layout(
    barmode='stack',
    xaxis_title="Count",
    height=300
)

# fig_fail_success.show()

st.plotly_chart(fig_fail_success, use_container_width=True)

# Pie chart of success vs failure

# Count status values
status_counts = df["Status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]

# Define custom color mapping
color_map = {
    "Success": "lightgreen",
    "Failed": "lightcoral",
    "Running": "lightyellow"
}

# Create pie chart with custom colors
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


