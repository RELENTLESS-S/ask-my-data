# import pandas as pd 

# df = pd.read_csv(r"S:\Ask_my _data\ask-my-data\data\raw\split_data.csv",sep = ";" ,encoding="latin1")

# print(df.head())
# print(repr(df.head()))

# print(df.info())

# Clean column names
# df.columns = (
#     df.columns
#     .str.strip()
#     .str.lower()
#     .str.replace(" ", "_")
# )

# print(df.isna().sum())

# print(df.shape)

# df = df.drop_duplicates()
# df = df.drop(columns=["image-url-s", "image-url-m", "image-url-l"], errors="ignore")

# # print(df.shape)

# df.to_csv(r"S:\Ask_my _data\ask-my-data\data\cleaned\clean01_data.csv", index=False)

# import pandas as pd
# df = pd.read_csv(r"S:\Ask_my _data\ask-my-data\data\cleaned\clean01_data.csv", encoding="latin1")
# print(df.columns.tolist())

# import pandas as pd


# def clean_isbn(isbn):
#     if pd.isna(isbn):
#         return None

#     isbn = str(isbn).strip()

#     # Remove hyphens and spaces
#     isbn = isbn.replace("-", "").replace(" ", "")

#     # Add leading zeros if shorter than ISBN-10
#     if isbn.isdigit() and len(isbn) < 10:
#         isbn = isbn.zfill(10)

#     return isbn


# df = pd.read_csv(r"S:\Ask_my _data\ask-my-data\data\cleaned\clean01_data.csv", dtype={"isbn": str})

# df["isbn"] = df["isbn"].apply(clean_isbn)

# df.to_csv(r"S:\Ask_my _data\ask-my-data\data\cleaned\books_corrected.csv", index=False)




import pandas as pd
from pathlib import Path

# 1. Input CSV file
csv_path = Path(
    r"S:\Ask_my _data\ask-my-data\data\cleaned\books_with_metadata_20261013_122611.csv"
)

# 2. Output CSV file
output_path = Path(
    r"S:\Ask_my _data\ask-my-data\data\cleaned\books_metadata_filtered.csv"
)

# 3. Read CSV
print("Reading CSV...")
df = pd.read_csv(csv_path, dtype={"isbn": str})

print(f"Original number of rows: {len(df)}")

# 4. Treat empty strings and whitespace-only values as missing
metadata_columns = ["subjects", "description"]

for col in metadata_columns:
    df[col] = df[col].replace(r"^\s*$", pd.NA, regex=True)

# 5. Remove rows where BOTH columns are empty
df_cleaned = df.dropna(
    subset=metadata_columns,
    how="all"
).copy()

# 6. Save to a new CSV file
df_cleaned.to_csv(output_path, index=False)

# 7. Report results
removed = len(df) - len(df_cleaned)

print(f"Rows removed: {removed}")
print(f"Rows remaining: {len(df_cleaned)}")
print(f"Filtered CSV saved to: {output_path}")
