import pandas as pd
from entsoe import EntsoePandasClient
from datetime import datetime, timedelta
import os
import requests
from bs4 import BeautifulSoup

csv_path = 'data/entsoe_lux.csv'

# User must set their ENTSO-E API key as an environment variable or directly here
API_KEY = os.environ.get("ENTSOE_API_KEY")
if not API_KEY:
    raise ValueError("ENTSOE_API_KEY environment variable not set.")
client = EntsoePandasClient(api_key=API_KEY)
country_code = 'LU'

# List of desired production types
production_types = [
    'Hydro Run-of-river and poundage',
    'Biomass',
    'Fossil Gas',
    'Hydro Water Reservoir',
    'Waste',
    'Wind Onshore',
    'Solar'
]

# Determine start and end dates for update
if os.path.exists(csv_path):
    existing = pd.read_csv(csv_path, header=0, skiprows=[1], index_col=0)
    existing.index = pd.to_datetime(existing.index)
    last_date = existing.index.max()
    # Download from 5 days before last_date to today
    start = last_date - pd.Timedelta(days=5)
    end = pd.Timestamp(datetime.utcnow(), tz=last_date.tz if last_date.tz else 'Europe/Brussels')
else:
    # If no file, download from 2020-01-01
    start = pd.Timestamp('2020-01-01T00:00', tz='Europe/Brussels')
    end = pd.Timestamp(datetime.utcnow(), tz='Europe/Brussels')
    existing = None

# Download actual generation per type (quarter-hourly)
gen = client.query_generation(country_code, start=start, end=end, psr_type=None)
gen_selected = gen[production_types]
# Download load data (quarter-hourly)
load = client.query_load(country_code, start=start, end=end)
# Combine into one DataFrame
result = gen_selected.copy()
result['Load'] = load

# Merge/append to existing data
if existing is not None:
    # Remove overlapping dates in existing for the update range
    mask = ~((existing.index >= result.index.min()) & (existing.index <= result.index.max()))
    existing = existing.loc[mask]
    # Append new data and sort
    updated = pd.concat([existing, result])
    updated = updated[~updated.index.duplicated(keep='last')].sort_index()
else:
    updated = result

# Save to CSV
updated.to_csv(csv_path)
print('ENTSO-E data updated and saved to entsoe_lux.csv')


# Download the latest ILR energy installations Excel file from data.public.lu
public_lu_url = "https://data.public.lu/fr/datasets/la-production-denergie-electrique-au-luxembourg-1/#/resources"
excel_filename = "ilr-energie-centrales-de-production-canton-commune-details-v2.xlsx"

try:
    page = requests.get(public_lu_url)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    # Find the download button/link for the Excel file
    link = soup.find("a", href=lambda h: h and h.endswith("ilr-energie-centrales-de-production-canton-commune-details-v2.xlsx"))
    if link and link.has_attr("href"):
        excel_download_url = link["href"]
        if not excel_download_url.startswith("http"):
            excel_download_url = "https://data.public.lu" + excel_download_url
        response = requests.get(excel_download_url)
        response.raise_for_status()
        with open("data/"+excel_filename, "wb") as f:
            f.write(response.content)
        print(f"Downloaded latest ILR energy installations Excel file to {excel_filename}")
    else:
        print("Could not find Excel download link on data.public.lu page.")
except Exception as e:
    print(f"Failed to download Excel file: {e}")


