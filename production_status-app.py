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
        color = 'background-color: lightblue'
    return [color] * len(row)

#scenario name
scenario = "erdc_baseline"
scenario_title = "ERDC BASELINE"

scenario = "a_optimal_sample_base"
scenario_title = "Optimal Sample BASE"

root_dirr = r'https://raw.githubusercontent.com/akhalid-twi/COJ-production/refs/heads/main'
# Load the CSV file
#csv_file = "updated_erdc_baseline_simulation_summary_full.csv"
csv_file = "a_optimal_sample_base_simulation_basic_summary.csv"


@st.cache_data(ttl=60)   # refresh every 60 seconds
def load_data(path):
    return pd.read_csv(path)
df= load_data(rf'{root_dirr}/{csv_file}')



# Rename columns to remove units for internal use, but keep units for display
column_renames = {
    "Max WSE (ft)": "Max WSE",
    "Max Depth (ft)": "Max Depth",
    "Max Velocity (ft/s)": "Max Velocity",
    "Max Volume (ft^3)": "Max Volume",
    "Max Flow Balance (ft^3/s)": "Max Flow Balance",
    "Max Wind (ft/s)": "Max Wind",
    "Mean BC (ft)": "Mean BC",
    "Max BC (ft)": "Max BC"
}
df.rename(columns=column_renames, inplace=True)

# Get the last modified time of the file
modified_timestamp = os.path.getmtime(csv_file)
modified_datetime = datetime.datetime.fromtimestamp(modified_timestamp)
current_datetime = datetime.datetime.now()
file_age = current_datetime - modified_datetime

# Streamlit app title
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
elif progress_percent < 75 and progress_percent > 99:
    st.warning("🔄 Almost there...")    
else:
    st.success("✅ Completed!")

# Filter simulations by status
success_df = df[df["Status"] == "Success"].copy()
failed_df = df[df["Status"] == "Failed"].copy()
running_df = df[df["Status"] == "Running"].copy()


# Simulated counts
completed_count = len(success_df) + len(failed_df)
running_count = len(running_df)
failed_count = len(failed_df)
successful_count = len(success_df)

#------------------------------
# Horizontal stacked bar: Completed vs Running
#------------------------------
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
    marker=dict(color='lightblue')
))
fig_completion.update_layout(
    barmode='stack',
    xaxis_title="Count",
    height=225
)
st.plotly_chart(fig_completion, use_container_width=True)

#------------------------------
# Pie chart of success vs failure
#------------------------------
status_counts = df["Status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]
color_map = {
    "Success": "lightgreen",
    "Failed": "lightcoral",
    "Running": "lightblue"
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




#------------------------------
## SU usage
#------------------------------

# Convert SUs to numeric
success_df["SUs"] = pd.to_numeric(success_df["SUs"], errors='coerce')
total_sus = success_df["SUs"].sum()

# SU usage plot
st.subheader("Service Units (SUs) Used per Successful Simulation")
st.markdown(f"**Total SUs Used:** {total_sus:,}")
fig_su = px.bar(success_df, x="Directory", y="SUs", color="SUs", title="SUs per Successful Run")
st.plotly_chart(fig_su, use_container_width=True)

#------------------------------
# Status Table
#------------------------------

#csv_file = "updated_erdc_baseline_simulation_summary_full.csv"
csv_file2 = "a_optimal_sample_base_simulation_summary_full.csv"


@st.cache_data(ttl=60)   # refresh every 60 seconds
def load_data2(path):
    return pd.read_csv(path)
df2= load_data2(rf'{root_dirr}/{csv_file2}')


# Rename columns to remove units for internal use, but keep units for display
column_renames = {
    "Max WSE (ft)": "Max WSE",
    "Max Depth (ft)": "Max Depth",
    "Max Velocity (ft/s)": "Max Velocity",
    "Max Volume (ft^3)": "Max Volume",
    "Max Flow Balance (ft^3/s)": "Max Flow Balance",
    "Max Wind (ft/s)": "Max Wind",
    "Mean BC (ft)": "Mean BC",
    "Max BC (ft)": "Max BC"
}
df2.rename(columns=column_renames, inplace=True)

# Status table
styled_df = df2.style.apply(highlight_status, axis=1)
st.subheader("Status Table")
st.dataframe(styled_df, use_container_width=True)

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
for col in column_renames.values():
    if col in df2.columns:
        df2[col] = pd.to_numeric(df2[col], errors='coerce')

# Plot each metric with units in y-axis label
metrics_with_units = {
#    "Max WSE": "Maximum Water Surface Elevation (ft)",
    "Max Depth": "Maximum Flood Depth (ft)",
    "Max Velocity": "Maximum Velocity (ft/s)",
    "Max Volume": "Maximum Volume (ft³)",
    "Max Flow Balance": "Maximum Flow Balance (ft³/s)",
#    "Max Wind": "Maximum Wind Speed (ft/s)",
#    "Mean BC": "Mean Downstream Boundary Condition (ft)",
#    "Max BC": "Maximum Downstream Boundary Condition (ft)",
#    "Max Wind": "Maximum Wind Speed (ft/s)",

}

#for col, title in metrics_with_units.items():
#    if col in df.columns:
#        fig = px.bar(df, x="Directory", y=col, title=title, labels={col: title})
#        st.plotly_chart(fig, use_container_width=True)

for col, title in metrics_with_units.items():
    if col in df2.columns:
        mean_val = df2[col].mean()
        colors = ['crimson' if val > mean_val else 'steelblue' for val in df2[col]]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df2["Directory"],
            y=df2[col],
            marker_color=colors,
            name=col
        ))
        fig.add_trace(go.Scatter(
            x=df2["Directory"],
            y=[mean_val] * len(df2),
            mode='lines',
            line=dict(color='black', dash='dash'),
            name='Mean'
        ))
        # Dummy traces for legend
        fig.add_trace(go.Bar(
            x=[None],
            y=[None],
            marker_color='crimson',
            name='Above Mean'
        ))
        fig.add_trace(go.Bar(
            x=[None],
            y=[None],
            marker_color='steelblue',
            name='Below Mean'
        ))
        fig.update_layout(
            title=title,
            xaxis_title="Directory",
            yaxis_title=title,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)



#--------------------------
# correlation metrics
#--------------------------

success_df = df2[df2["Status"] == "Success"].copy()

success_df_clean = success_df.copy()
for cols in ['SUs','Max WSE','Failure Info','Failure Reason','Mean BC','Max BC','Max Wind']:
     del success_df_clean[cols]

st.subheader("Correlation Metrics")

# rearrange columns
success_df_clean = success_df_clean[['Vol Error (%)','Vol Error (AF)','Max Depth','Max Velocity','Max Volume','Max Flow Balance']]

corr_matrix = success_df_clean.select_dtypes(include='number').corr()
fig_corr = go.Figure(data=go.Heatmap(
     z=corr_matrix.values,
     x=corr_matrix.columns,
     y=corr_matrix.columns,
     colorscale='Viridis'
 ))
st.plotly_chart(fig_corr, use_container_width=True)

