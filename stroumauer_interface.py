import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
from streamlit import columns

# Load the Excel file
file_path = r'C:/Users/notyo/Documents/02_Aner_Engagementer/Stroumauer/data/ilr-energie-centrales-de-production-canton-commune-details-v2.xlsx'
df = pd.read_excel(file_path)

# Filter for photovoltaics only
pv_type_col = "Type d'installation"
df = df[df[pv_type_col] == 'Installation photovoltaïque']

# Group by 'Commune' and sum the 'Puissance (kW)' column (assuming this is the power column)
power_col = 'Sum of Puissance installée (kW)'
commune_col = 'Commune'

if commune_col in df.columns and power_col in df.columns:
    df_grouped = df.groupby(commune_col, as_index=False)[power_col].sum()
else:
    st.error(f"Could not find columns '{commune_col}' and/or '{power_col}' in the data.")
    st.stop()

# Load coordinates from adresses.csv instead of geopy
adresses_path = r'C:/Users/notyo/Documents/02_Aner_Engagementer/Stroumauer/data/addresses.csv'
adresses_df = pd.read_csv(adresses_path, sep=";")
# Only keep relevant columns and average lat/lon per commune
adresses_df = adresses_df[['commune', 'lat_wgs84', 'lon_wgs84']]
adresses_df = adresses_df.groupby('commune', as_index=False).agg({'lat_wgs84': 'mean', 'lon_wgs84': 'mean'})
# Ensure column names are lower case for merge
adresses_df.columns = [c.lower() for c in adresses_df.columns]
# Merge on commune name (case-insensitive)


df_grouped = pd.merge(
    df_grouped,
    adresses_df.rename(columns={'commune': commune_col, 'lat_wgs84': 'Latitude', 'lon_wgs84': 'Longitude'}),
    on=commune_col,
    how='left'
)
# Remove communes where coordinates are missing
for col in ['Latitude', 'Longitude']:
    df_grouped[col] = pd.to_numeric(df_grouped[col], errors='coerce')
df_grouped = df_grouped.dropna(subset=['Latitude', 'Longitude'])

# Before displaying the dataframe, ensure all columns are string or numeric and handle special characters
for col in df_grouped.columns:
    if df_grouped[col].dtype == object:
        df_grouped[col] = df_grouped[col].astype(str)
        df_grouped[col] = df_grouped[col].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')

# Streamlit app
st.title('ILR Energie Centrales de Production - Power by Commune')
st.write('This app displays the total installed power per commune in Luxembourg.')

# --- Combined interactive map for all energy sources ---
energy_types = {
    'Installation photovoltaïque': {'color': 'rgb(255, 215, 0)', 'label': 'Solar'},
    'Eolienne': {'color': 'rgb(135, 206, 235)', 'label': 'Wind'},
    'Biomasse solide': {'color': 'rgb(144, 238, 144)', 'label': 'Biomass'},
    'Hydro': {'color': 'rgb(31, 119, 180)', 'label': 'Hydro'}
}

# Load and concatenate all types
all_types = list(energy_types.keys())
df_all = pd.read_excel(file_path)
df_hydro = df_all[df_all[pv_type_col].str.contains('Hydro', case=False, na=False)].copy()
df_hydro[pv_type_col] = 'Hydro'
df_other = df_all[df_all[pv_type_col].isin([t for t in all_types if t != 'Hydro'])].copy()
df_combined = pd.concat([df_other, df_hydro], ignore_index=True)

# Group by commune and technology
df_combined_grouped = df_combined.groupby([commune_col, pv_type_col], as_index=False)[power_col].sum()
df_combined_grouped = pd.merge(
    df_combined_grouped,
    adresses_df.rename(columns={'commune': commune_col, 'lat_wgs84': 'Latitude', 'lon_wgs84': 'Longitude'}),
    on=commune_col,
    how='left'
)
for col in ['Latitude', 'Longitude']:
    df_combined_grouped[col] = pd.to_numeric(df_combined_grouped[col], errors='coerce')
df_combined_grouped = df_combined_grouped.dropna(subset=['Latitude', 'Longitude'])
for col in df_combined_grouped.columns:
    if df_combined_grouped[col].dtype == object:
        df_combined_grouped[col] = df_combined_grouped[col].astype(str)
        df_combined_grouped[col] = df_combined_grouped[col].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')

color_map = {k: v['color'] for k, v in energy_types.items()}
fig_all_installed = px.scatter_mapbox(
    df_combined_grouped,
    lat='Latitude',
    lon='Longitude',
    size=power_col,
    color=pv_type_col,
    color_discrete_map=color_map,
    hover_name=commune_col,
    size_max=30,
    zoom=8,
    mapbox_style='open-street-map',
    title='Total Installed Power by Commune and Technology (Map)'
)
fig_all_installed.update_layout(height=800, width=800)
st.markdown('---')
st.subheader('Total Installed Power by Commune and Technology')
st.plotly_chart(fig_all_installed, use_container_width=True)


# --- Actual production chart from CSV ---
import matplotlib.pyplot as plt

csv_path = r"C:/Users/notyo/Documents/02_Aner_Engagementer/Stroumauer/data/entsoe_lux.csv"
prod_cols = ['Load', 'Hydro Run-of-river and poundage', 'Wind Onshore', 'Solar', "Biomass", 'Fossil Gas', 'Waste']

# Read CSV, skip the second row (header=0, skiprows=[1])
prod_df = pd.read_csv(csv_path, header=0, skiprows=[1], index_col=0)
prod_df = prod_df[prod_cols]  # Filter to keep only relevant columns

# Convert date column to datetime
prod_df.index = pd.to_datetime(prod_df.index)

# --- Add filter for day, week, month, year, or custom range ---
st.markdown('---')
st.subheader('Actual Electricity Production in Luxembourg')

now = prod_df.index.max()
default_start = now - pd.Timedelta(days=7)
default_end = now

col1, col2 = st.columns(2)
with col1:
    user_start = st.date_input("Start date", value=default_start.date(), min_value=prod_df.index.min().date(), max_value=now.date())
with col2:
    user_end = st.date_input("End date", value=default_end.date(), min_value=prod_df.index.min().date(), max_value=now.date())

# Ensure prod_df.index and user_start_dt/user_end_dt are both tz-naive or both tz-aware
user_start_dt = pd.to_datetime(user_start)
user_end_dt = pd.to_datetime(user_end)

# Convert prod_df.index to DatetimeIndex if not already, handling tz-aware objects
if not isinstance(prod_df.index, pd.DatetimeIndex):
    # If any tz-aware datetimes, convert to UTC first
    if any(hasattr(x, 'tzinfo') and x.tzinfo is not None for x in prod_df.index):
        prod_df.index = pd.to_datetime(prod_df.index, utc=True)
    else:
        prod_df.index = pd.to_datetime(prod_df.index)

index_tz = getattr(prod_df.index, 'tz', None)

# Convert prod_df.index to DatetimeIndex if not already
if not isinstance(prod_df.index, pd.DatetimeIndex):
    prod_df.index = pd.to_datetime(prod_df.index)

if index_tz is not None:
    # If index is tz-aware, localize user dates to the same tz
    if user_start_dt.tzinfo is None:
        user_start_dt = user_start_dt.tz_localize(index_tz)
    else:
        user_start_dt = user_start_dt.tz_convert(index_tz)
    if user_end_dt.tzinfo is None:
        user_end_dt = user_end_dt.tz_localize(index_tz)
    else:
        user_end_dt = user_end_dt.tz_convert(index_tz)
    # Ensure prod_df.index is tz-aware
    if prod_df.index.tz is None:
        prod_df.index = prod_df.index.tz_localize(index_tz)
else:
    # If index is tz-naive, make user dates tz-naive and prod_df.index tz-naive
    if user_start_dt.tzinfo is not None:
        user_start_dt = user_start_dt.tz_convert(None)
    if user_end_dt.tzinfo is not None:
        user_end_dt = user_end_dt.tz_convert(None)
    if hasattr(prod_df.index, 'tz') and prod_df.index.tz is not None:
        prod_df.index = prod_df.index.tz_convert(None)

if user_start_dt > user_end_dt:
    st.warning("Start date must be before end date.")
    mask = slice(None)
else:
    mask = (prod_df.index >= user_start_dt) & (prod_df.index <= user_end_dt)

prod_df_filtered = prod_df.loc[mask]

# Plot using Plotly for Streamlit (stacked area for production, line for Load)
import plotly.graph_objects as go
fig_prod = go.Figure()

# Define production columns (excluding 'Load')
production_cols = [col for col in prod_cols if col != 'Load']
# Assign custom colors: Solar (yellow), Wind (light blue), Biomass (green), others as you wish
custom_colors = {
    'Solar': '#FFD700',            # yellow
    'Wind Onshore': '#87CEEB',    # light blue
    'Biomass': '#228B22',         # green
    'Hydro Run-of-river and poundage': '#1f77b4',
    'Fossil Gas': '#a9a9a9',
    'Waste': '#8B4513'
}

# Add stacked area traces for production
for col in production_cols:
    fig_prod.add_trace(go.Scatter(
        x=prod_df_filtered.index,
        y=prod_df_filtered[col],
        mode='lines',
        name=col,
        stackgroup='one',
        line=dict(width=0.5, color=custom_colors.get(col, None)),
        fill='tonexty',
        groupnorm=None
    ))
# Add Load as a line on top
fig_prod.add_trace(go.Scatter(
    x=prod_df_filtered.index,
    y=prod_df_filtered['Load'],
    mode='lines',
    name='Load',
    line=dict(width=2, color='black'),
    fill=None
))
fig_prod.update_layout(title='Actual Electricity Production in Luxembourg',
                      xaxis_title='Date (GMT+2)',
                      yaxis_title='Power (MW)',
                      height=500,
                      legend_title='Source',
                      template='plotly_white')
st.plotly_chart(fig_prod, use_container_width=True)


# --- Plot number of added cooperatives per month from PDF ---
import re
from collections import Counter
import matplotlib.dates as mdates

pdf_path = r'C:/Users/notyo/Documents/02_Aner_Engagementer/Stroumauer/data/ilr-elc-pub-Communautes-Energetiques.pdf'

try:
    import PyPDF2
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
except ImportError:
    st.warning('PyPDF2 is not installed. Please install it to enable PDF parsing.')
    text = ""
except Exception as e:
    st.warning(f'Could not read PDF: {e}')
    text = ""

# Try to find all dates in the format dd/mm/yyyy or dd.mm.yyyy or yyyy-mm-dd
# Adjust regex as needed for your PDF's date format
if text:
    date_patterns = [
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{2}\.\d{2}\.\d{4})',
        r'(\d{4}-\d{2}-\d{2})'
    ]
    dates = []
    for pat in date_patterns:
        dates += re.findall(pat, text)
    # Normalize all dates to pandas datetime
    parsed_dates = []
    for d in dates:
        for fmt in ('%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d'):
            try:
                parsed_dates.append(pd.to_datetime(d, format=fmt))
                break
            except Exception:
                continue
    if parsed_dates:
        # Count number of new cooperatives per month
        months = [dt.strftime('%Y-%m') for dt in parsed_dates]
        month_counts = Counter(months)
        month_series = pd.Series(month_counts).sort_index()
        # Make cumulative
        cumulative_series = month_series.cumsum()
        # Ensure all months are present in the index
        if not cumulative_series.empty:
            all_months = pd.date_range(start=cumulative_series.index[0], end=cumulative_series.index[-1], freq='MS').strftime('%Y-%m')
            cumulative_series = cumulative_series.reindex(all_months, method='ffill').fillna(0)
        # Plot
        st.markdown('---')
        st.subheader('Number of Cooperatives')
        fig_coop = px.bar(
            x=cumulative_series.index,
            y=cumulative_series.values,
            labels={'x': 'Month', 'y': 'Cumulative Number of Energy Sharing Communities (CEL, CER or CEN)'},
            title='Cumulative Number of CEL, CER or CEN'
        )
        st.plotly_chart(fig_coop, use_container_width=True)
    else:
        st.info('No valid dates found in the PDF for cooperative creation.')
else:
    st.info('No text could be extracted from the PDF.')

# --- Extract energy communities and postcodes from PDF and plot on map ---

if text:
    # Extract community names and siège social (address)
    # Example regex: community name, siège social (address with L-xxxx), date
    # Improved extraction: match community name, any text, L-xxxx, any text, date
    # This will work even if there are line breaks or inconsistent separators
    community_pattern = r'([A-Za-zÀ-ÿ0-9\- ]+)\s+([\s\S]*?L-\d{4}[\s\S]*?)(\d{2}/\d{2}/\d{4}|\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})'
    communities = re.findall(community_pattern, text, re.DOTALL)

    # Build dataframe
    if communities:
        df_communities = pd.DataFrame(communities, columns=['Community', 'Siège social', 'Date'])
        # Extract postcode from Siège social robustly
        df_communities['Postcode'] = df_communities['Siège social'].str.extract(r'(L-\d{4})', expand=False)
        df_communities['Postcode'] = df_communities['Postcode'].str.extract(r'(\d{4})', expand=False)
        df_communities['Date'] = pd.to_datetime(df_communities['Date'], errors='coerce')
        # Geocode postcodes using addresses.csv
        adresses_post_df = pd.read_csv(adresses_path, sep=';')
        adresses_post_df['postcode'] = adresses_post_df['code_postal'].astype(str).str.extract(r'(\d{4})', expand=False)
        adresses_post_df = adresses_post_df[['postcode', 'lat_wgs84', 'lon_wgs84']].drop_duplicates('postcode')
        df_communities = pd.merge(df_communities, adresses_post_df, left_on='Postcode', right_on='postcode', how='left')
        # Drop communities without coordinates
        df_communities = df_communities.dropna(subset=['lat_wgs84', 'lon_wgs84'])
        # Add extra info to hover: 'Nom de la Communauté énergétique', 'Date de la dernière notification', 'Raison sociale'
        # If these columns exist in df_communities, add them to hover_data
        hover_cols = ['Postcode', 'Date', 'Siège social']
        for extra_col in ['Nom de la Communauté énergétique', 'Date de la dernière notification', 'Raison sociale']:
            if extra_col in df_communities.columns:
                hover_cols.append(extra_col)
        fig_comm_map = px.scatter_mapbox(
            df_communities,
            lat='lat_wgs84',
            lon='lon_wgs84',
            hover_name='Community',
            hover_data=hover_cols,
            color_discrete_sequence=['red'],
            zoom=8,
            mapbox_style='open-street-map',
            title='Energy Communities by Location (Postcode)'
        )
        fig_comm_map.update_layout(height=600)
        st.markdown('---')
        st.subheader('Energy Communities by Location (Postcode)')
        st.plotly_chart(fig_comm_map, use_container_width=True)
    else:
        st.info('No energy communities with postcodes found in the PDF.')

# --- Distribution of PV installation sizes (Bubble Plot, one bubble per installation, vertically jittered) ---
st.markdown('---')
st.subheader('Distribution of PV Installation Sizes (kW)')

import numpy as np
pv_sizes = df['Sum of Puissance installée (kW)'].dropna().astype(float)
# Add vertical jitter to y for each bubble
np.random.seed(42)  # For reproducibility
pv_bubble_df = pd.DataFrame({'Installed Power (kW)': pv_sizes, 'y': np.random.uniform(-0.5, 0.5, size=len(pv_sizes))})

fig_pv_bubble = px.scatter(
    pv_bubble_df,
    x='Installed Power (kW)',
    y='y',
    size=[8]*len(pv_bubble_df),  # All bubbles same size for visual clarity
    color='Installed Power (kW)',
    color_continuous_scale='Viridis',
    labels={'Installed Power (kW)': 'Installed Power (kW)'},
    title='Bubble Plot of PV Installation Sizes (One Bubble per Installation)',
    size_max=12,
    height=600
)
fig_pv_bubble.update_traces(marker=dict(line=dict(width=0.1)))  # Remove bubble contour
fig_pv_bubble.update_layout(
    xaxis_title='Installed Power (kW)',
    yaxis_title='',
    yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    height=600,
    coloraxis_showscale=False
)
st.plotly_chart(fig_pv_bubble, use_container_width=True)



