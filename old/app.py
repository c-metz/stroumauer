import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Dummy data for power production in Luxembourg
def get_dummy_production_data():
    now = datetime.now()
    times = [now - timedelta(hours=i) for i in range(24)][::-1]
    data = {
        'Time': times,
        'Solar': [10 + i * 0.5 for i in range(24)],
        'Wind': [20 + i * 0.3 for i in range(24)],
        'Hydro': [15 + i * 0.2 for i in range(24)],
        'Biomass': [5 + i * 0.1 for i in range(24)],
        'Fossil': [30 - i * 0.4 for i in range(24)],
    }
    return pd.DataFrame(data)

# Streamlit app
st.title("Power Production in Luxembourg")
st.write("This app visualizes today's power production in Luxembourg using dummy data.")

# Fetch dummy data
data = get_dummy_production_data()

# Melt the data for stacked area chart
melted_data = data.melt(id_vars='Time', var_name='Source', value_name='Production (MW)')

# Display data
st.subheader("Production Data")
st.dataframe(data)

# Plot production data using Plotly
st.subheader("Production Today")
fig = px.area(
    melted_data,
    x='Time',
    y='Production (MW)',
    color='Source',
    title="Power Production in Luxembourg (Today)",
    labels={'Production (MW)': 'Production (MW)', 'Time': 'Time'},
)
fig.update_layout(xaxis=dict(tickangle=45), yaxis_title="Production (MW)")
st.plotly_chart(fig)