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

## Week 6: Feature Engineering and Market Metrics

Analyzed the January 2024–September 2026 cleaned Residential Sold dataset from Weeks 4–5, preserving all 495,207 records and the existing monthly mortgage-rate enrichment.

### Script and inputs

- `week6_feature_engineering.py` — validated Week 6 pipeline, alongside the other weekly scripts.
- `CRMLS data/CRMLSSoldCombined_202401_202609_cleaned.csv` — cleaned sold input.
- `CRMLS data/CRMLSListingCombined_202401_202609_cleaned.csv` — inspected separately for metric applicability; no listings feature output is generated.
- `school_districts/DistrictAreas2425.shp` and its companion files — locally extracted [California School District Areas 2024–25](https://data.ca.gov/dataset/california-school-district-areas-2024-25/resource/7dfaf005-58eb-45db-93b1-7aff091b2172).

MLS datasets, boundary files, and private outputs are not included in this commit. The script stops with a clear error if required local inputs are missing.

### Features and district enrichment

- Calculates `PriceRatio` and `CloseToOriginalListRatio` as `ClosePrice / OriginalListPrice`, and `PricePerSqFt` as `ClosePrice / LivingArea`, using positive price/denominator values.
- Validates existing `DaysOnMarket`, derives `Year`, `Month`, and `YrMo` from `CloseDate`, and calculates listing-to-contract and contract-to-close days.
- Treats `ListingContractDate` as the listing agreement effective date; its interval may differ from MLS DaysOnMarket.
- Uses GeoPandas to intersect valid property coordinates with elementary, high school, and unified district boundaries. Coordinate systems are aligned, invalid polygon geometries are repaired in memory, and no nearest-district matching is used.
- Preserves original MLS school fields, retains unmatched records, and flags same-type ambiguous matches while keeping all candidate district names/IDs.
- Creates four summaries: property type/subtype, county/MLS area, listing office, and buyer office. Includes transaction counts, per-metric valid counts, and flags for groups smaller than 10 records.

### Validation and interpretation

The validated local run preserved 495,207 input/output rows. Price formulas, duplicate ratio equality, day intervals, date parts, source attributes, mortgage fields, and all four segment transaction totals passed checks. An independent CSV read-back also passed.

| School district matching | Records |
|---|---:|
| Valid coordinates | 490,363 |
| Matched to at least one district | 490,155 |
| Unmatched | 5,052 |
| Same-type ambiguous matches | 0 |

The match rate was 98.98% of all records and 99.96% of records with valid coordinates. Seven invalid district geometries were repaired in memory without changing the source files.

Missing numeric values remain missing. Negative DOM/date intervals remain flagged in detail and are excluded from summary statistics. Very long positive intervals and pre-2000 contract dates are flagged for review. The data contains 379 repeated ListingKeys beyond their first occurrence; records are retained, so transaction counts are source-record counts rather than deduplicated sales.

Some very small positive original list prices produce extreme ratios: the median PriceRatio was 0.9945 while its mean was 50.63. Review these source values before interpreting mean ratios. The 2024–25 boundaries are applied across the entire period and do not establish historical school attendance eligibility.

### Run locally

Dependencies: Python, pandas, NumPy, GeoPandas, and Shapely. The validated Anaconda base run used Python 3.13.9, pandas 2.2.3, NumPy 2.1.3, and GeoPandas 1.2.0.

From the repository root:

```bash
/opt/anaconda3/bin/python week6_feature_engineering.py
```

The project root is inferred from the script location. To use inputs in a different project folder:

```bash
/opt/anaconda3/bin/python week6_feature_engineering.py --project-dir "/path/to/project"
```

### Local outputs and Tableau

Outputs are written to `outputs/private/week6/`; reruns create timestamped subfolders instead of overwriting existing outputs:

- `week6_sold_enriched.csv`
- `week6_feature_sample.csv` — 20 example records.
- `week6_summary_property_type.csv`
- `week6_summary_geography.csv`
- `week6_summary_list_office.csv`
- `week6_summary_buyer_office.csv`
- `week6_metric_quality.csv`, `week6_validation.json`, and `week6_validation_report.txt`.

Use the detailed enriched CSV for Tableau monthly filters and trends. The four summaries cover the entire period. Format ratios as percentages, display transaction/valid-value counts, and review invalid flags and source outliers before presenting averages. Recompute statistics from detail rather than averaging summary medians or unweighted group means.

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
