#!/usr/bin/env python
# coding: utf-8

# ### Sold Data

import pandas as pd
import glob

sold_files = sorted(glob.glob("CRMLSSold20????*.csv"))
sold_dfs = []

for file in sold_files:
    df = pd.read_csv(file)
    print(f"{file}: {len(df)} rows")
    sold_dfs.append(df)


# Row count before concatenation
sold_rows_before = sum(len(df) for df in sold_dfs)
print("Total sold rows before concatenation:", sold_rows_before)
sold = pd.concat(sold_dfs, ignore_index = True)
# Row count after concatenation
sold_rows_after = len(sold)
print("Total sold rows after concatenation:", sold_rows_after)

# Row count before Residential filter
sold_before_filter = len(sold)
sold = sold[sold["PropertyType"] == "Residential"]

# Row count after Residential filter
sold_after_filter = len(sold)
print("Sold rows before Residential filter:", sold_before_filter)
print("Sold rows after Residential filter:", sold_after_filter)

sold.to_csv("CRMLSSoldCombined_202401_202609.csv", index=False)


# ### Listing Data

# Find all monthly listing CSV files
listing_files = sorted(glob.glob("CRMLSListing20????.csv"))

# Read each monthly listing file into a DataFrame
listing_dfs = []

for file in listing_files:
    df = pd.read_csv(file)
    print(f"{file}: {len(df)} rows")
    listing_dfs.append(df)

# Row count before concatenation
listing_rows_before_concat = sum(len(df) for df in listing_dfs)
print("Listing rows before concatenation:", listing_rows_before_concat)

# Combine all monthly listing datasets
listings = pd.concat(listing_dfs, ignore_index=True)

# Row count after concatenation
listing_rows_after_concat = len(listings)
print("Listing rows after concatenation:", listing_rows_after_concat)

# Row count before Residential filter
listing_rows_before_filter = len(listings)

# Keep Residential properties only
listings = listings[listings["PropertyType"] == "Residential"]

# Row count after Residential filter
listing_rows_after_filter = len(listings)

print("Listing rows before Residential filter:", listing_rows_before_filter)
print("Listing rows after Residential filter:", listing_rows_after_filter)

# Save combined listing dataset
listings.to_csv("CRMLSListingCombined_202401_202609.csv", index=False)
print("Week 1 aggregation complete.")

