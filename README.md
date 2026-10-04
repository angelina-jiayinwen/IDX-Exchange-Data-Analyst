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

Coming soon.

## Tools Used

- Python
- Pandas
- JupyterLab
- Git
- GitHub

## Repository Files

- `week1_aggregation.py` – Monthly dataset aggregation and Residential property filtering.
- `.gitignore` – Prevents confidential datasets and local environment files from being uploaded.
