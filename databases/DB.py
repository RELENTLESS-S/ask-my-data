import pandas as pd
import sqlite3

# 1. Path to your CSV file
csv_path = r"S:\Ask_my _data\ask-my-data\data\cleaned\books_metadata_filtered.csv"

# 2. Path where you want to create the SQLite database file
db_path = r"S:\Ask_my _data\ask-my-data\databases\books_database.db"

# 3. Load the CSV data into Pandas (keeping ISBNs as strings to preserve leading zeros)
print("Reading CSV data...")
df = pd.read_csv(csv_path, dtype={"isbn": str})

# 4. Establish a connection to the SQLite database
# (If the file doesn't exist, SQLite will automatically create it)
conn = sqlite3.connect(db_path)

# 5. Write the DataFrame records into a SQL table named 'books'
print("Writing data to SQLite database...")
df.to_sql(name="books", con=conn, if_exists="replace", index=False)

# Close the database connection
conn.close()

print(f"\n🎉 SQLite database successfully created at:\n➡️ {db_path}")
