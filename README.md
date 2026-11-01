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
