"""
Weeks 2-3 (continued): Mortgage Rate Enrichment

This script fetches the national 30-year fixed mortgage rate from FRED
(MORTGAGE30US), converts weekly values into monthly averages, and left-merges
those rates onto the Week 1 Residential combined Sold and Listings datasets.
"""

from pathlib import Path
import pandas as pd

# Week 1 combined Residential files live outside this GitHub repo.
# Use the current local folder that actually contains the CSVs.
DATA_DIR = Path('/Users/angelinawen/Desktop/work_work_work/CRMLS data')

SOLD_INPUT = DATA_DIR / 'CRMLSSoldCombined_202401_202609.csv'
LISTINGS_INPUT = DATA_DIR / 'CRMLSListingCombined_202401_202609.csv'

# New output names so the original Week 1 files stay unchanged.
SOLD_OUTPUT = DATA_DIR / 'CRMLSSoldCombined_202401_202609_with_mortgage_rates.csv'
LISTINGS_OUTPUT = DATA_DIR / 'CRMLSListingCombined_202401_202609_with_mortgage_rates.csv'

FRED_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US'


def fetch_and_resample_mortgage_rates():
    """Download weekly FRED rates and collapse them to one average per month."""
    print('\n' + '=' * 65)
    print('STEP 1: FETCH FRED MORTGAGE30US')
    print('=' * 65)

    # parse_dates turns the date column into true datetime values
    # so we can later group by calendar month with .dt.to_period('M').
    mortgage = pd.read_csv(FRED_URL, parse_dates=['observation_date'])

    # Rename to the handbook names: date + rate_30yr_fixed.
    mortgage.columns = ['date', 'rate_30yr_fixed']
    print('Weekly FRED rows:', len(mortgage))
    print('Weekly FRED date range:', mortgage['date'].min(), 'to', mortgage['date'].max())
    print('First five weekly rows:\n', mortgage.head().to_string(index=False))

    # '.' in FRED files can mean a missing observation. Convert those to NaN.
    mortgage['rate_30yr_fixed'] = pd.to_numeric(mortgage['rate_30yr_fixed'], errors='coerce')
    print('Weekly rows with missing rates:', mortgage['rate_30yr_fixed'].isna().sum())

    print('\n' + '=' * 65)
    print('STEP 2: RESAMPLE WEEKLY RATES TO MONTHLY AVERAGES')
    print('=' * 65)

    # Period('M') is a year-month key such as 2024-01.
    # Several Thursday observations in January all become 2024-01.
    mortgage['year_month'] = mortgage['date'].dt.to_period('M')

    # groupby().mean() calculates the average weekly rate inside each month.
    # reset_index() turns year_month from an index back into a regular column
    # so we can merge on it later.
    mortgage_monthly = (
        mortgage.groupby('year_month')['rate_30yr_fixed']
        .mean()
        .reset_index()
    )

    print('Monthly rate rows after resampling:', len(mortgage_monthly))
    print('Monthly year_month range:',
          mortgage_monthly['year_month'].min(), 'to', mortgage_monthly['year_month'].max())

    # A valid monthly lookup table must have one row per year_month.
    duplicate_months = mortgage_monthly['year_month'].duplicated().sum()
    print('Duplicate year_month keys in monthly rates:', duplicate_months)
    if duplicate_months:
        print(mortgage_monthly.loc[mortgage_monthly['year_month'].duplicated(keep=False)])
        raise ValueError('Monthly mortgage table has duplicate year_month keys.')

    missing_monthly_rates = mortgage_monthly['rate_30yr_fixed'].isna().sum()
    print('Months with a missing average rate:', missing_monthly_rates)
    if missing_monthly_rates:
        print(mortgage_monthly.loc[mortgage_monthly['rate_30yr_fixed'].isna()])

    return mortgage_monthly


def add_year_month(df, date_column):
    """Build a year_month Period key from an MLS date column."""
    # errors='coerce' turns unreadable dates into NaT instead of crashing.
    parsed_dates = pd.to_datetime(df[date_column], errors='coerce')
    n_missing_raw = df[date_column].isna().sum()
    n_unparsed = parsed_dates.isna().sum()
    print(f'  Raw missing {date_column}: {n_missing_raw:,}')
    print(f'  Unparsed or missing {date_column} after to_datetime: {n_unparsed:,}')
    if n_unparsed:
        print('  Sample rows with missing/unparsed dates:')
        print(df.loc[parsed_dates.isna(), [date_column]].head().to_string(index=False))

    year_month = parsed_dates.dt.to_period('M')
    return year_month, parsed_dates


def validate_merge(kind, original_df, merged_df, date_column, parsed_dates, mortgage_monthly):
    """Check that the left merge kept every MLS row and report unmatched rates."""
    print('\n' + '-' * 65)
    print(f'VALIDATION: {kind.upper()}')
    print('-' * 65)

    print(f'Rows before merge: {len(original_df):,}')
    print(f'Rows after merge:  {len(merged_df):,}')
    if len(merged_df) != len(original_df):
        raise ValueError(
            f'{kind}: left merge changed the row count. '
            'Check for duplicate year_month keys in the mortgage table.'
        )
    print('Row count unchanged after left merge: yes')

    unmatched = merged_df['rate_30yr_fixed'].isna()
    n_unmatched = int(unmatched.sum())
    print(f'Unmatched mortgage rates (rate_30yr_fixed is null): {n_unmatched:,}')

    if n_unmatched == 0:
        print('Every row received a monthly mortgage rate.')
        print(
            merged_df[[date_column, 'year_month', 'rate_30yr_fixed']].head().to_string(index=False)
        )
        return

    # Do not fill unmatched rates. Explain why they did not join.
    unmatched_rows = merged_df.loc[unmatched].copy()
    unmatched_rows['_parsed_date'] = parsed_dates.loc[unmatched]

    missing_date = unmatched_rows['_parsed_date'].isna()
    min_rate_month = mortgage_monthly['year_month'].min()
    max_rate_month = mortgage_monthly['year_month'].max()
    outside_range = (
        ~missing_date
        & (
            (unmatched_rows['year_month'] < min_rate_month)
            | (unmatched_rows['year_month'] > max_rate_month)
        )
    )
    inside_range_but_unmatched = ~missing_date & ~outside_range

    print('Unmatched breakdown (not filled):')
    print(f'  Missing or unparsed {date_column}: {int(missing_date.sum()):,}')
    print(f'  year_month outside FRED monthly range '
          f'({min_rate_month} to {max_rate_month}): {int(outside_range.sum()):,}')
    print(f'  year_month inside FRED range but still unmatched: '
          f'{int(inside_range_but_unmatched.sum()):,}')

    unmatched_months = (
        unmatched_rows['year_month']
        .value_counts(dropna=False)
        .rename_axis('year_month')
        .reset_index(name='unmatched_rows')
    )
    print('Unmatched year_month values and row counts:')
    print(unmatched_months.to_string(index=False))


def enrich_dataset(kind, input_path, date_column, output_path, mortgage_monthly):
    """Load one MLS dataset, merge monthly rates, validate, and save a new CSV."""
    print('\n' + '=' * 65)
    print(f'STEP 3-5: ENRICH {kind.upper()} DATASET')
    print('=' * 65)
    print('Reading:', input_path)

    if not input_path.exists():
        raise FileNotFoundError(
            f'Input not found: {input_path}\n'
            'Check the path to your Week 1 Residential-filtered CSV.'
        )

    # low_memory=False asks pandas to scan the whole file before guessing dtypes.
    df = pd.read_csv(input_path, low_memory=False)
    print(f'Loaded {kind} rows, columns:', df.shape)

    if date_column not in df.columns:
        raise KeyError(f'{kind} is missing required date column: {date_column}')

    print(f'Creating year_month from {date_column} with to_datetime() and to_period("M")')
    df['year_month'], parsed_dates = add_year_month(df, date_column)

    # how='left' keeps every MLS row even if a month has no mortgage rate.
    # on='year_month' matches the Period key created on both tables.
    merged = df.merge(mortgage_monthly, on='year_month', how='left')
    validate_merge(kind, df, merged, date_column, parsed_dates, mortgage_monthly)

    preview_cols = [date_column, 'year_month', 'rate_30yr_fixed']
    if kind == 'sold' and 'ClosePrice' in merged.columns:
        preview_cols.insert(2, 'ClosePrice')
    print('Preview after merge:')
    print(merged[preview_cols].head().to_string(index=False))

    # index=False avoids writing the pandas row numbers as an extra column.
    merged.to_csv(output_path, index=False)
    print(f'Saved new enriched file (original not overwritten): {output_path}')
    return merged


def main():
    mortgage_monthly = fetch_and_resample_mortgage_rates()

    enrich_dataset(
        kind='sold',
        input_path=SOLD_INPUT,
        date_column='CloseDate',
        output_path=SOLD_OUTPUT,
        mortgage_monthly=mortgage_monthly,
    )
    enrich_dataset(
        kind='listings',
        input_path=LISTINGS_INPUT,
        date_column='ListingContractDate',
        output_path=LISTINGS_OUTPUT,
        mortgage_monthly=mortgage_monthly,
    )

    print('\nFinished Weeks 2-3 mortgage rate enrichment.')
    print('Original combined CSVs were not modified.')


if __name__ == '__main__':
    main()
