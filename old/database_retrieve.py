import sqlite3
import pandas as pd

# Path to the database
db_path = 'entsoe_power_data.db'

# Connect to the database
conn = sqlite3.connect(db_path)

# Query to retrieve data
query = "SELECT * FROM power_data;"  # Replace 'your_table_name' with the actual table name

# Load data into a pandas DataFrame
df = pd.read_sql_query(query, conn)

# Close the connection
conn.close()

# Display the DataFrame
print(df)