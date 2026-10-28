import pandas as pd 

# with open (r"S:\Ask_my _data\ask-my-data\data\raw\split_data.csv", encoding="latin1") as f:
#     for line_number, line in enumerate(f, start=1):
#         if 50 <= line_number <= 60:
#             print(f"Row {line_number}: {repr(line)}")

file_path = r"S:\Ask_my _data\ask-my-data\data\cleaned\clean01_data.csv"
df = pd.read_csv(file_path, sep=",", encoding="latin1")


# print(df.head())
# print(df.info())
print(df["isbn"].describe())

'''
This code provides with a cleanup and sorting for any abnormal or malformed isbn in the dataset considers thrm to ne in the range (10< & 13>) and using regex to remove any hyphens or spaces in the isbn column.
'''
# 1. Convert the column to string and remove any hyphens or spaces 
isbn_str = df['isbn'].astype(str).str.replace(r'[\s-]', '', regex=True)

# 2. Filter for lengths less than 10 OR greater than 13
malformed_books = df[(isbn_str.str.len() < 10) | (isbn_str.str.len() > 13)]

# 3. View the results
print(f"Found {len(malformed_books)} rows with invalid lengths.")
print(malformed_books)
