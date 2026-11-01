# IDX Exchange Data Analyst Internship

This repository contains Python data analysis work completed during my Data Analyst Internship with IDX Exchange.

The project uses Python and Pandas to process, validate, and analyze CRMLS residential real estate data from January 2024 onward.

> Note: MLS transaction datasets are confidential internship data and are not included in this repository.

## Project Progress

### Week 1 – Monthly Dataset Aggregation

Combined monthly CRMLS Sold and Listing datasets from January 2024 through September 2026 into consolidated datasets for analysis.

Tasks completed:
- Loaded monthly Sold and Listing CSV files using Pandas.
- Concatenated 33 monthly files for each dataset.
- Verified row counts before and after concatenation.
- Filtered both datasets to `PropertyType == "Residential"`.
- Verified row counts before and after filtering.
- Exported the processed datasets as new CSV files for local analysis.

File:
- `week1_aggregation.py`

#### Row Count Validation

##### Sold Dataset

| Processing stage | Row count |
|---|---:|
| Before concatenation | 736,355 |
| After concatenation | 736,355 |
| Before Residential filter | 736,355 |
| After Residential filter | 495,207 |

##### Listing Dataset

| Processing stage | Row count |
|---|---:|
| Before concatenation | 1,022,950 |
| After concatenation | 1,022,950 |
| Before Residential filter | 1,022,950 |
| After Residential filter | 650,461 |

### Weeks 2–3 – Dataset Structuring and Validation

Conducted exploratory data analysis (EDA) on the Residential-filtered CRMLS Sold and Listings datasets produced in Week 1, focusing on dataset structure, completeness, numeric distributions, and potential data-quality issues before cleaning.

Tasks completed:
- Inspected dataset dimensions, column names, and data types for both datasets.
- Verified that both datasets contain only PropertyType == "Residential" records.
- Calculated missing-value counts and percentages for all columns, flagging those with more than 90% missing values.
- Identified core analytical fields to retain and nonessential, high-missing columns for further review.
- Generated descriptive statistics, including minimum, maximum, mean, median, and percentile summaries for nine key numeric fields where available.
- Created histograms and boxplots to examine numeric distributions and identify potential extreme outliers.
- Conducted preliminary EDA on sale prices, days on market, sale-to-list price comparisons, date consistency, and county-level median prices.
- Generated local CSV reports, visualizations, and EDA findings to inform subsequent data cleaning.

File:
- 'week2_3_dataset_validation.py' – Dataset validation, missing-value analysis, numeric EDA, outlier screening, and preliminary market analysis for both Sold and Listings datasets

### Generated EDA Outputs

The following analysis reports and visualizations were generated for both Residential Sold and Listings datasets and are available in this repository with supervisor approval.

**Reports and summaries:**
- Column structure and property-type summary reports
- Missing-value reports and columns exceeding 90% missingness
- Numeric distribution and percentile summaries
- Potential outlier screening reports
- EDA findings and county-level median price summaries (where applicable)

**Visualizations:**
- Histograms for key numeric variables
- Boxplots for identifying potential extreme outliers

**GitHub output directories:**
- `outputs/public/sold/` – Sold dataset EDA reports and plots
- `outputs/public/listings/` – Listings dataset EDA reports and plots

- ## Weeks 2–3 (Continued): Mortgage Rate Enrichment

### Objective
Enrich the combined Residential sold and listings datasets with the national 30-year fixed mortgage rate from the Federal Reserve Economic Data (FRED) database. This provides additional economic context for analyzing California residential real estate market trends.

### Data Source
- **Source:** Federal Reserve Economic Data (FRED)
- **Series:** MORTGAGE30US — 30-Year Fixed Rate Mortgage Average in the United States
- **Original Frequency:** Weekly
- **Target Frequency:** Monthly
- **Source URL:** https://fred.stlouisfed.org/series/MORTGAGE30US

### Data Processing
The `mortgage_rate_enrichment.py` script performs the following operations:

1. Retrieves historical mortgage rates directly from FRED using Pandas.
2. Converts observation dates to datetime format and groups weekly observations by year and month.
3. Calculates the monthly average mortgage rate.
4. Creates a matching `year_month` key for both MLS datasets:
   - **Sold:** Based on `CloseDate`
   - **Listings:** Based on `ListingContractDate`
5. Performs left joins to add the monthly mortgage rate (`rate_30yr_fixed`) to each dataset.
6. Validates the merged datasets by checking missing mortgage rates and ensuring that row counts are preserved.
7. Exports the enriched datasets as new CSV files without overwriting the original data.

### Deliverables
- `mortgage_rate_enrichment.py` — Reproducible Python script for fetching, processing, merging, and validating mortgage rate data.
- Two enriched CSV datasets containing the original MLS records and the additional `rate_30yr_fixed` column.
- Validation output reporting unmatched mortgage rates and confirming row-count consistency.

- ## Weeks 4–5: Data Cleaning and Preparation

### Objective
Prepare the mortgage-enriched Residential Sold and Listings datasets for downstream analysis and feature engineering by standardizing data types, identifying inconsistencies, and evaluating data quality.

### Data Cleaning and Validation

The `week4_5_data_cleaning.py` script performs the following operations:

1. **Dataset Inspection**
   - Loads the mortgage-enriched Residential Sold and Listings datasets.
   - Reports original row counts, column counts, data types, and missing-value summaries.

2. **Date Standardization**
   - Converts `CloseDate`, `PurchaseContractDate`, `ListingContractDate`, and `ContractStatusChangeDate` to datetime where available.
   - Converts invalid date strings to `NaT` and reports conversion failures.

3. **Redundant Column Review**
   - Identifies potentially redundant or unnecessary columns.
   - Documents proposed removals while preserving all columns unless explicitly approved.

4. **Missing Values and Numeric Validation**
   - Reports missing values before and after cleaning.
   - Converts relevant numeric columns using Pandas.
   - Flags invalid closing prices, nonpositive living areas, negative days on market, and negative bedroom or bathroom counts.
   - Preserves missing and suspicious values for further investigation rather than automatically deleting records.

5. **Date Consistency Checks**
   - Creates `listing_after_close_flag`, `purchase_after_close_flag`, and `negative_timeline_flag`.
   - Reports the number of records violating each date consistency rule.

6. **Geographic Data Quality**
   - Flags missing or zero coordinates, positive longitude values, globally implausible coordinates, and coordinates outside an approximate California bounding box.
   - Preserves original latitude and longitude values.

### Outputs
- `week4_5_data_cleaning.py` — Reproducible data cleaning and validation script.
- `CRMLSSoldCombined_202401_202609_cleaned.csv` — Cleaned Residential Sold dataset.
- `CRMLSListingCombined_202401_202609_cleaned.csv` — Cleaned Residential Listings dataset.
- `week4_5_validation_summary.csv` — Consolidated validation results for both datasets.
- Additional CSV reports covering missing values, date conversions, numeric conversions, and proposed column removals.

### Data Preservation
Original combined and mortgage-enriched datasets are not overwritten. The cleaning process preserves all rows, adds data quality flags, and retains columns needed for subsequent feature engineering.

**Note:** Large MLS datasets and private validation reports are stored locally and excluded from the GitHub repository according to `.gitignore`.

## Tools Used

- Python
- Pandas
- JupyterLab
- Git
- GitHub
- Matplotlib

## Repository Files

- `week1_aggregation.py` – Monthly dataset aggregation and Residential property filtering.
- `.gitignore` – Prevents confidential datasets and local environment files from being uploaded.
- `week2_3_dataset_validation.py` – Residential dataset validation, missing-value analysis, numeric distribution review, and exploratory data analysis.
- `outputs/public/sold/` – Approved Sold dataset EDA reports and visualizations.
- `outputs/public/listings/` – Approved Listings dataset EDA reports and visualizations.
