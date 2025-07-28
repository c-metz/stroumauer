import sqlite3
import pandas as pd
from datetime import datetime, timedelta, timezone
from entsoe import EntsoePandasClient

# ENTSOE API configuration
ENTSOE_API_KEY = "bc2fa864-d946-41c3-883f-8e14da565893"

# SQLite database configuration
DB_PATH = "entsoe_power_data.db"

# Initialize the ENTSOE client
client = EntsoePandasClient(api_key=ENTSOE_API_KEY)

def fetch_entsoe_data(start_date, end_date, country_code):
    """
    Fetch power data from ENTSOE using entsoe-py.
    """
    try:
        df = client.query_generation(
            country_code, 
            start=pd.Timestamp(start_date).tz_convert('UTC'), 
            end=pd.Timestamp(end_date).tz_convert('UTC'), 
            psr_type=None
        )

        df = df.reset_index()
        df["timestamp"] = df["index"].dt.strftime("%Y-%m-%d %H:%M:%S")

        print(df.head())  # Debugging line to check the fetched data

        return df
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def setup_database():
    """
    Set up the SQLite database if it doesn't exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS power_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            country_code TEXT NOT NULL,
            generation_type TEXT NOT NULL,
            value REAL NOT NULL,
            UNIQUE(timestamp, country_code, generation_type)
        )
    """)
    conn.commit()
    conn.close()

def store_data_in_db(dataframe, country_code):
    """
    Store the data in the SQLite database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(dataframe.head())  # Debugging line to check the dataframe before storing
    print(dataframe.columns)

    for _, row in dataframe.iterrows():
        for generation_type in ['Biomass', 'Fossil Gas', 'Hydro Run-of-river and poundage',
                                'Hydro Water Reservoir', 'Solar', 'Waste', 'Wind Onshore']:
            if generation_type in row:
                try:
                    cursor.execute("""
                        INSERT INTO power_data (timestamp, country_code, generation_type, value)
                        VALUES (?, ?, ?, ?)
                    """, (row['timestamp'], country_code, generation_type, row[generation_type]))
                except sqlite3.IntegrityError:
                    # Skip if the data already exists
                    pass
    conn.commit()
    conn.close()

    pass  # Removed unused variable


def update_power_data(country_code, days):
    """
    Update the power data for the last `days` days.
    """
    setup_database()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    dataframe = fetch_entsoe_data(start_date, end_date, country_code)
    if not dataframe.empty:
        store_data_in_db(dataframe, country_code)


if __name__ == "__main__":
    update_power_data("LU", days=7)
