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

Generated outputs (stored locally, excluded from GitHub):
- Column structure and property-type summary reports
- Missing-value reports and columns exceeding 90% missingness
- Numeric distribution and percentile summaries
- Histograms and boxplots
- Potential outlier reports
- EDA findings and county-level price summaries

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
