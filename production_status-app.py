import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# Load the CSV file
csv_file = "erdc_baseline_simulation_summary.csv"
df = pd.read_csv(csv_file)

# Streamlit app title
st.title("ERDC Baseline Simulation Dashboard")

# Display the full data table
st.subheader("Simulation Results Table")
st.dataframe(df)

# Filter successful and failed simulations
success_df = df[df["Status"] == "Success"].copy()
failed_df = df[df["Status"] == "Failed"].copy()

# Convert SUs to numeric
success_df["SUs"] = pd.to_numeric(success_df["SUs"], errors='coerce')

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