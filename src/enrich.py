
from datetime import datetime
import os
import time
import pandas as pd
import requests

# 1. Path to your original source file
source_path = (
    r"S:\Ask_my _data\ask-my-data\data\cleaned\books_corrected.csv"
)

# 2. Path for the output file

output_dir = os.path.dirname(source_path)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

new_csv_path = os.path.join(
    output_dir,
    f"books_with_metadata_{timestamp}.csv"
)

failed_path = os.path.join(output_dir, "failed_isbns.csv")

# Load original data
df = pd.read_csv(source_path, dtype={"isbn": str})

# Ensure destination columns exist
for col in ["description", "subjects"]:
    if col not in df.columns:
        df[col] = ""

failed_isbns = []

# Test with 5 records first.
# Change to len(df) after testing.
limit = len(df)

with requests.Session() as session:
    for idx in range(limit):
        isbn_no = df.at[idx, "isbn"]

        # Skip missing ISBNs
        if pd.isna(isbn_no) or not str(isbn_no).strip():
            failed_isbns.append({
                "row": idx,
                "isbn": "",
                "reason": "Missing ISBN"
            })
            continue

        isbn_no = str(isbn_no).strip()

        # Correct URL
        url = f"https://openlibrary.org/isbn/{isbn_no}.json"

        try:
            response = session.get(url, timeout=15)

            print(
                f"Processing row {idx + 1} | "
                f"ISBN: {isbn_no} | "
                f"Status: {response.status_code}"
            )

            response.raise_for_status()
            data = response.json()

            # Extract subjects
            raw_subjects = data.get("subjects", [])
            if isinstance(raw_subjects, list):
                clean_subjects = ", ".join(
                    str(subject) for subject in raw_subjects
                )
            else:
                clean_subjects = ""

            # Extract description
            raw_desc = data.get("description", "")

            if isinstance(raw_desc, dict):
                clean_desc = raw_desc.get("value", "")
            elif isinstance(raw_desc, str):
                clean_desc = raw_desc
            else:
                clean_desc = ""

            df.at[idx, "description"] = clean_desc
            df.at[idx, "subjects"] = clean_subjects

            # A successful request may still lack metadata
            if not clean_desc and not clean_subjects:
                print(f"No description/subjects for {isbn_no}")

        except requests.exceptions.RequestException as e:
            print(f"Request failed for ISBN {isbn_no}: {e}")
            failed_isbns.append({
                "row": idx,
                "isbn": isbn_no,
                "reason": str(e)
            })

        except ValueError as e:
            print(f"Invalid JSON for ISBN {isbn_no}: {e}")
            failed_isbns.append({
                "row": idx,
                "isbn": isbn_no,
                "reason": "Invalid JSON"
            })

        # Be polite to the API
        time.sleep(1)

# Save enriched data to a new CSV
df.to_csv(new_csv_path, index=False)

# Save failed ISBNs separately
pd.DataFrame(
    failed_isbns,
    columns=["row", "isbn", "reason"]
).to_csv(failed_path, index=False)

print(f"\nEnriched CSV saved to:\n{new_csv_path}")
print(f"Failed ISBNs saved to:\n{failed_path}")
