# -*- coding: utf-8 -*-
"""
Created on Wed Jan 14 15:01:15 2026

@author: akhalid
"""

import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
import datetime
import os
from time import sleep
from stqdm import stqdm
import requests
from datetime import datetime, timezone

# =============================================================================
# Helper functions
# =============================================================================

def get_last_modified(repo_owner, repo_name, file_path):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
    params = {"path": file_path, "page": 1, "per_page": 1}
    r = requests.get(url, params=params)

    if r.status_code == 200:
        commit = r.json()[0]
        timestamp = commit["commit"]["committer"]["date"]
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return None

# Define a function to apply row-wise styling
def highlight_status(row):
    color = ''
    if row['Status'] == 'SUCCESS':
        color = 'background-color: lightgreen'
    elif "failed" in row['Status'].lower():
        color = 'background-color: lightcoral'
    elif row['Status'] == 'Running':
        color = 'background-color: lightblue'
    return [color] * len(row)

# =============================================================================
# File Paths
# =============================================================================

#scenario name
scenario = "erdc_baseline"
scenario_title = "ERDC BASELINE"

scenario = "a_optimal_sample_base"
scenario_title = "Optimal Sample BASE"

root_dirr = r'https://raw.githubusercontent.com/akhalid-twi/COJ-production/refs/heads/main/assets'

# =============================================================================
# # Load the CSV file
# =============================================================================

csv_file = f"{scenario}_simulation_basic_summary.csv" # basic information
csv_file2 = f"{scenario}_simulation_HDF_summary.csv"  # HDF extracted information


@st.cache_data(ttl=60)   # refresh every 60 seconds
def load_data(path):
    return pd.read_csv(path)

df= load_data(rf'{root_dirr}/{csv_file}')


df['_index'] = df.Directory
df = df.set_index('_index')


@st.cache_data(ttl=60)   # refresh every 60 seconds
def load_data2(path):
    return pd.read_csv(path,index_col='folder')

df2= load_data2(rf'{root_dirr}/{csv_file2}')

#------------------------------
# merging data from both csvs
#------------------------------

df['Max WSE (ft)']=df2['max_wse']
df['Max Depth (ft)']=df2['max_depth']
df['Max Volume (ft^3)']=df2['max_volume']
df['Max Flow Balance (ft^3/s)']=df2['max_flow_balance']
df['Max Stage BC (ft)']=df2['max_bc_stage']
df['Max Inflow BC (cfs)']=df2['max_bc_flow']
df['Max Cum PRCP (in)']=df2['max_cum_prcp']

df = df.sort_values(by='Directory')
df = df.reset_index(drop=True)


# =============================================================================
# # check last file modification
# =============================================================================

if 'githubusercontent' not in root_dirr:

    modified_timestamp = os.path.getmtime(f'{root_dirr}/{csv_file}')

    # MAKE TZ-AWARE
    modified_datetime = datetime.fromtimestamp(modified_timestamp, tz=timezone.utc)

else:
    modified_datetime = get_last_modified(
        "akhalid-twi",
        "COJ-production",
        f"assets/{csv_file}"
    )

    # Ensure GitHub datetime is timezone-aware
    if modified_datetime.tzinfo is None:
        modified_datetime = modified_datetime.replace(tzinfo=timezone.utc)

print(modified_datetime)



current_datetime = datetime.now(timezone.utc)
file_age = current_datetime - modified_datetime

# =============================================================================
# Streamlit app title
# =============================================================================

st.title("COJ Production Dashboard")
st.subheader(f" Scenario: {scenario_title} Conditions")
st.markdown(f"Last updated: {str(modified_datetime)[:-6]}")

total_simulations = 10000
completed_simulations = len(df)
st.subheader(f"Simulation Count: {completed_simulations}/{total_simulations}")


#------------------------------
# Progress tag
#------------------------------
progress_percent = int((completed_simulations / total_simulations) * 100)
progress_text = f"Processing simulations... {progress_percent}% complete"
my_bar = st.progress(progress_percent, text=progress_text)


# Optional: Add a status message
if progress_percent < 25:
    st.info("🚧 Just getting started...")
elif progress_percent < 75:
    st.warning("🔄 In progress...")
elif progress_percent > 75 and progress_percent < 99.5:
    st.warning("🔄 Almost there...")    
else:
    st.error("✅ Completed!")

#------------------------------
# Show tentative completion
#------------------------------
# Tentative dates
start_date = datetime(2026, 1, 1)
completion_date = datetime(2026, 1, 15)

# Current time
now = datetime.now()

# Calculate remaining time
remaining_time = completion_date - now

# Display timeline
st.subheader("Timeline")
st.write(f"Production Started: {start_date.strftime('%d %b %Y')}")
st.write(f"Production Completion (projected): {completion_date.strftime('%d %b %Y')}")

# Countdown timer
days = remaining_time.days
hours, remainder = divmod(remaining_time.seconds, 3600)
minutes, seconds = divmod(remainder, 60)

# Check if we are past the completion date

# Check timeline status
remaining_seconds = remaining_time.total_seconds()

if remaining_seconds >= 0:
    # Countdown still active
    st.info(f"Time Remaining: {days} days, {hours} hrs, {minutes} min")

elif remaining_seconds < 0 and progress_percent < 99.5:
    # Project overdue but not yet technically complete
    st.error(f"Project overdue: {days} days, {hours} hrs, {minutes} min")

elif remaining_seconds < 0 and progress_percent >= 99.5:
    # Completed beyond target date
    st.info(f"Completed {abs(days)} days ago")

# =============================================================================
# Status Count
# =============================================================================

# Filter simulations by status
success_df = df[df["Status"] == "SUCCESS"].copy()
failed_df = df[df["Status"].str.contains("Failed", case=False, na=False)]
running_df = df[df["Status"] == "Running"].copy()


# Simulated counts
completed_count = len(success_df) + len(failed_df)
running_count = len(running_df)
failed_count = len(failed_df)
successful_count = len(success_df)


waiting_count = total_simulations - (completed_count + running_count)
waiting_count = max(0, waiting_count)


#------------------------------
# Horizontal stacked bar: Completed vs Running
#------------------------------
st.subheader("Completed vs Running Simulations (Stacked)")


completed_count = len(success_df) + len(failed_df)
running_count = len(running_df)
waiting_count = total_simulations - (completed_count + running_count)
waiting_count = max(waiting_count, 0)  # avoid negative

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
    marker=dict(color='skyblue')
))

fig_completion.add_trace(go.Bar(
    y=["Simulations"],
    x=[waiting_count],
    name="Waiting",
    orientation='h',
    marker=dict(color='lightgray')
))

fig_completion.update_layout(
    barmode='stack',
    xaxis_title="Count",
    xaxis=dict(range=[0, total_simulations]),
    height=225
)

st.plotly_chart(fig_completion)


#------------------------------
# Vertical Bar chart of status categories
#------------------------------
st.subheader("Simulation Status Distribution")

# Get value counts
status_counts = df["Status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]

# Define custom colors for each status
color_map = {
    "SUCCESS": "#90EE90",
    "Running": "skyblue",
    "UNSTABLE-FAILED": "#FF7F7F",
    "SLURM_TIMEOUT-FAILED": "#FFD700",
    "DISK-FAILED": "#FFD700",
    "HDF-FAILED": "#FFD700"
}

status_counts["Color"] = status_counts["Status"].map(color_map).fillna("orange")

# Create Plotly bar chart
fig_status = go.Figure()

for _, row in status_counts.iterrows():
    fig_status.add_trace(go.Bar(
        x=[row["Status"]],
        y=[row["Count"]],
        name=row["Status"],
        marker_color=row["Color"],
        text=row["Count"],
        textposition="outside"
    ))

fig_status.update_layout(
    title="Status Type Counts",
    xaxis_title="Status",
    yaxis_title="Count",
    showlegend=False,
    height=500,
    yaxis=dict(range=[0, 10000])  # Set y-axis range
)

st.plotly_chart(fig_status)

#------------------------------
# Pie chart of success vs failure
#------------------------------
status_counts = df["Status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]

color_map = {
    "SUCCESS": "#90EE90",        # Light Green (Success)
    "Running": "skyblue",        # Light Blue (In Progress)
    "UNSTABLE-FAILED": "#FF7F7F",# Soft Red (Unstable Failure)
    "SLURM_TIMEOUT-FAILED": "#FFA500", # Orange (Timeout)
    "DISK-FAILED": "#FFD700",    # Gold (Disk Issue)
    "HDF-FAILED": "#FFD700",     # Gold (HDF Issue)
    "FAILED": "#FF6347"          #
}

fig_pie = px.pie(
    status_counts,
    names="Status",
    values="Count",
    title="Failure vs Success Distribution",
    color="Status",
    color_discrete_map=color_map
)
#st.subheader("Simulation Status Distribution")
st.plotly_chart(fig_pie)


# =============================================================================
#  SU usage
# =============================================================================

# Convert SUs to numeric
success_df["SUs"] = pd.to_numeric(success_df["SUs"], errors='coerce')
total_sus = success_df["SUs"].sum()

# SU usage plot
st.subheader("Service Units (SUs) Used per Successful Simulation")
st.markdown(f"**Total SUs Used:** {total_sus:,}")
fig_su = px.bar(success_df, x="Directory", y="SUs", color="SUs", title="SUs per Successful Run")
st.plotly_chart(fig_su)


# =============================================================================
# Error plots for key metrics
# =============================================================================

st.subheader("Error plots for key metrics")

# Convert columns to numeric
df["Vol Error (AF)"] = pd.to_numeric(df["Vol Error (AF)"], errors='coerce')
df["Vol Error (%)"] = pd.to_numeric(df["Vol Error (%)"], errors='coerce')
df["Max WSEL Err"] = pd.to_numeric(df["Max WSEL Err"], errors='coerce')


def categorize_by_status(status):
    status = str(status).strip().lower()

    if status == "success":
        return "Success"         # green
    elif status == "running":
        return "Running"         # cyan
    elif "failed" in status:
        return "Failed"          # red
    else:
        return "Other"           # orange

# Apply to each metric
df["Color Category WSEL"]  = df["Status"].apply(categorize_by_status)
df["Color Category VolAF"] = df["Status"].apply(categorize_by_status)
df["Color Category VolPct"] = df["Status"].apply(categorize_by_status)

# Color map (simple)
color_map = {
    "Success": "green",
    "Running": "cyan",
    "Failed": "red",
    "Other": "orange"
}


df_sorted = df.sort_values(by='Directory')




#------------------------------
# Plot for Max WSEL Err
#------------------------------

fig_max_wsel_er = px.bar(
    df_sorted,
    x="Directory",
    y="Max WSEL Err",
    title="Max WSEL Error",
    color="Color Category WSEL",
    color_discrete_map=color_map
)
fig_max_wsel_er.update_yaxes(range=[0, 20])
st.plotly_chart(fig_max_wsel_er, config={"responsive": True})


#------------------------------
# Plot for Vol Error (AF)
#------------------------------

fig_vol_af = px.bar(
    df_sorted,
    x="Directory",
    y="Vol Error (AF)",
    title="Volume Error (AF)",
    color="Color Category VolAF",
    color_discrete_map=color_map
)
fig_vol_af.update_yaxes(range=[0, 100000])
st.plotly_chart(fig_vol_af, config={"responsive": True})


#------------------------------
# Plot for Vol Error (%)
#------------------------------

fig_vol_pct = px.bar(
    df_sorted,
    x="Directory",
    y="Vol Error (%)",
    title="Volume Error (%)",
    color="Color Category VolPct",
    color_discrete_map=color_map
)
fig_vol_pct.update_yaxes(range=[0, 2])
st.plotly_chart(fig_vol_pct, config={"responsive": True})



# =============================================================================
# Status Table
# =============================================================================
for cols in ['Color Category WSEL', 'Color Category VolAF','Color Category VolPct', 'Max Cum PRCP (inc)']:
    if cols in df.columns:
        del df[cols]





# Status table
styled_df = df.style.apply(highlight_status, axis=1)

st.subheader("Status Table")
st.dataframe(styled_df)

#------------------------------
# Available Plan to Review
#------------------------------

#st.subheader("Available QC files to Review")
notebook_url = "https://github.com/akhalid-twi/COJ-production/blob/a6fc0713035084895f43efde2e3915ecd67960e5/example_qc/results_S0155_notebook.ipynb"
download_url = "https://raw.githubusercontent.com/akhalid-twi/COJ-production/a6fc0713035084895f43efde2e3915ecd67960e5/example_qc/results_S0155_notebook.html"

#st.markdown(f'<a href="{notebook_url}" target="_blank">🔗 View Notebook for S0155 (code blocks are not hidden)</a>', unsafe_allow_html=True)
#st.markdown(f'<a href="{download_url}" download target="_blank">⬇️ Download HTML Report for S0155</a>', unsafe_allow_html=True)


#------------------------------
# Hydrodynamic and forcing plots
#------------------------------
st.subheader("Hydrodynamic Model Outputs and Forcings")

# Convert relevant columns to numeric
for col in df.columns:
    if col not in ['Directory','Status','Failure Reason','Start Time','End Time']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Plot each metric with units in y-axis label
metrics_with_units = {
#    "Max WSE (ft)": "Maximum Water Surface Elevation (ft)",
    "Max Depth (ft)": "Maximum Flood Depth (ft)",
#    "Max Velocity": "Maximum Velocity (ft/s)",
    "Max Volume (ft^3)": "Maximum Volume (ft³)",
    "Max Flow Balance (ft^3/s)": "Maximum Flow Balance (ft³/s)",
    "Max Stage BC (ft)": "Maximum Downstream Boundary Condition (ft)",
    "Max Inflow BC (cfs)": "Maximum Inflow Boundary Condition (cfs)",
    "Max Cum PRCP (in)": "Maximum Cumulative PRCP Depth (inc)",

}


for col, title in metrics_with_units.items():
    if col in df.columns:
        #print(col)
        #mean_val = df[col].mean()
        mean_val  = round(df[col].quantile(0.95), 2)

        colors = ['purple' if val > mean_val else 'steelblue' for val in df[col]]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["Directory"],
            y=df[col],
            marker_color=colors,
            name=col
        ))
        fig.add_trace(go.Scatter(
            x=df["Directory"],
            y=[mean_val] * len(df),
            mode='lines',
            line=dict(color='black', dash='dash'),
            name='95%'
        ))
        # Dummy traces for legend
        fig.add_trace(go.Bar(
            x=[None],
            y=[None],
            marker_color='purple',
            name='Above 95%'
        ))
        fig.add_trace(go.Bar(
            x=[None],
            y=[None],
            marker_color='steelblue',
            name='Below 95%'
        ))
        fig.update_layout(
            title=title,
            xaxis_title="Directory",
            yaxis_title=title,
            showlegend=True
        )

        ymax = mean_val * 1.5
        fig.update_yaxes(range=[0, ymax])
        
        if col == 'Max Cum PRCP (in)':
            fig.update_yaxes(range=[0, 100])
        elif col == 'Max Stage BC (ft)':
            fig.update_yaxes(range=[0, 15])
            
             

        st.plotly_chart(fig)



#--------------------------
# correlation metrics
#--------------------------

success_df = df[df["Status"] == "SUCCESS"].copy()

success_df_clean = success_df.copy()
for cols in ['SUs','Max WSE (ft)','Failure Info','Failure Reason']:
    if cols in success_df_clean.columns:
        del success_df_clean[cols]

st.subheader("Correlation Metrics")
#print(success_df_clean.columns)


# rearrange columns
success_df_clean = success_df_clean[['Vol Error (%)','Vol Error (AF)','Max Depth (ft)',
                                     'Max Volume (ft^3)',
                                     'Max Flow Balance (ft^3/s)', 'Max Stage BC (ft)',
                                     'Max Inflow BC (cfs)', 'Max Cum PRCP (in)']]


corr_matrix = success_df_clean.select_dtypes(include='number').corr()
fig_corr = go.Figure(data=go.Heatmap(
     z=corr_matrix.values,
     x=corr_matrix.columns,
     y=corr_matrix.columns,
     colorscale='Viridis'
 ))
st.plotly_chart(fig_corr)

