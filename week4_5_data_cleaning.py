#!/usr/bin/env python
# coding: utf-8

"""
Weeks 4-5: Data Cleaning and Preparation

This script inspects the mortgage-enriched Residential Sold and Listings
datasets, converts dates and numeric fields, adds quality-flag columns, and
saves new cleaned CSVs.

It does not overwrite Week 1 combined files or the mortgage-enriched files.
It does not drop rows.
It does not drop columns unless they are listed in APPROVED_COLUMNS_TO_DROP.
That list starts empty on purpose so potentially useful fields are kept
until you approve any removals.
"""

from pathlib import Path
import pandas as pd

# Same local data folder used by mortgage_rate_enrichment.py.
DATA_DIR = Path('/Users/angelinawen/Desktop/work_work_work/CRMLS data')
SOLD_INPUT = DATA_DIR / 'CRMLSSoldCombined_202401_202609_with_mortgage_rates.csv'
LISTINGS_INPUT = DATA_DIR / 'CRMLSListingCombined_202401_202609_with_mortgage_rates.csv'

# New filenames so earlier CSVs stay unchanged.
SOLD_OUTPUT = DATA_DIR / 'CRMLSSoldCombined_202401_202609_cleaned.csv'
LISTINGS_OUTPUT = DATA_DIR / 'CRMLSListingCombined_202401_202609_cleaned.csv'

# Validation tables are local/private and gitignored with other outputs/*.
REPORT_DIR = Path('outputs/private/week4_5')

DATE_FIELDS = [
    'CloseDate',
    'PurchaseContractDate',
    'ListingContractDate',
    'ContractStatusChangeDate',
]

# Numeric fields needed for Weeks 4-6, plus mortgage rate.
NUMERIC_FIELDS = [
    'ClosePrice',
    'ListPrice',
    'OriginalListPrice',
    'LivingArea',
    'LotSizeAcres',
    'BedroomsTotal',
    'BathroomsTotalInteger',
    'DaysOnMarket',
    'YearBuilt',
    'Latitude',
    'Longitude',
    'rate_30yr_fixed',
]

# Fields that later weeks need for metrics, maps, and Tableau filters.
WEEK6_REQUIRED_FIELDS = [
    'ClosePrice',
    'OriginalListPrice',
    'ListPrice',
    'LivingArea',
    'DaysOnMarket',
    'CloseDate',
    'ListingContractDate',
    'PurchaseContractDate',
    'PropertyType',
    'PropertySubType',
    'CountyOrParish',
    'City',
    'PostalCode',
    'MLSAreaMajor',
    'ListOfficeName',
    'BuyerOfficeName',
    'ListAgentFullName',
    'Latitude',
    'Longitude',
    'year_month',
    'rate_30yr_fixed',
]

# Approximate California bounding box in WGS84 degrees.
# This is a rectangle around the state, NOT a precise CA polygon or shapefile.
# Source of the rounded extents: commonly used CA geographic limits
# (about 32.5N-42.0N, 124.5W-114.1W).
CA_LAT_MIN = 32.5
CA_LAT_MAX = 42.0
CA_LON_MIN = -124.5
CA_LON_MAX = -114.1

# Leave this empty until you approve specific drops.
APPROVED_COLUMNS_TO_DROP = []

# Proposed only. The script reports these; it will not drop them automatically.
PROPOSED_REDUNDANT_COLUMNS = {
    'PropertyType.1': 'Duplicate listing column created when monthly files were concatenated.',
    'ListAgentFirstName.1': 'Duplicate of ListAgentFirstName.',
    'ListAgentLastName.1': 'Duplicate of ListAgentLastName.',
    'DaysOnMarket.1': 'Duplicate of DaysOnMarket.',
    'LivingArea.1': 'Duplicate of LivingArea.',
    'ListPrice.1': 'Duplicate of ListPrice.',
    'CloseDate.1': 'Duplicate of CloseDate.',
    'Latitude.1': 'Duplicate of Latitude.',
    'Longitude.1': 'Duplicate of Longitude.',
    'BuyerOfficeName.1': 'Duplicate of BuyerOfficeName.',
    'UnparsedAddress.1': 'Duplicate of UnparsedAddress.',
    'ListingKeyNumeric': 'Numeric copy of ListingKey; ListingKey is already unique.',
    'StreetNumberNumeric': 'Street number only; not used in Week 6 metrics or Tableau filters.',
    'AboveGradeFinishedArea': '100% missing in Weeks 2-3 EDA.',
    'CoveredSpaces': '100% missing in Weeks 2-3 EDA.',
    'TaxAnnualAmount': '100% missing in Weeks 2-3 EDA.',
    'TaxYear': '100% missing in Weeks 2-3 EDA.',
    'ElementarySchoolDistrict': '100% missing in Weeks 2-3 EDA.',
    'MiddleOrJuniorSchoolDistrict': '100% missing in Weeks 2-3 EDA.',
    'FireplacesTotal': '100% missing in Weeks 2-3 EDA.',
    'BusinessType': '100% missing in Weeks 2-3 EDA.',
    'BelowGradeFinishedArea': '>99% missing in Weeks 2-3 EDA.',
    'CoBuyerAgentFirstName': '>90% missing; not required for Week 6 or Tableau.',
    'BuilderName': '>95% missing; not required for Week 6.',
    'LotSizeDimensions': '>94% missing; LotSizeAcres is the lot-size field to keep.',
    'BuildingAreaTotal': '>91% missing; LivingArea is the size field used in PPSF.',
    'WaterfrontYN': '>99% missing on sold; not required later.',
    'BasementYN': '>98% missing on sold; not required later.',
    'latfilled': 'Incomplete coordinate-fill indicator; original Latitude is retained.',
    'lonfilled': 'Incomplete coordinate-fill indicator; original Longitude is retained.',
}


def present_columns(df, columns):
    """Return only column names that actually exist in this dataset."""
    return [col for col in columns if col in df.columns]


def missing_summary(df):
    """Build a missing-value table like the Weeks 2-3 EDA report."""
    summary = pd.DataFrame({
        'column': df.columns,
        'dtype': df.dtypes.astype(str).values,
        'null_count': df.isna().sum().values,
        'null_percent': (df.isna().mean() * 100).values,
    }).sort_values('null_percent', ascending=False)
    return summary


def save_table(df, path, index=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    print(f'Saved: {path}')


def inspect_dataset(kind, path):
    print('\n' + '=' * 65)
    print(f'STEP 1: INSPECT {kind.upper()} DATASET')
    print('=' * 65)
    print('Reading:', path)
    if not path.exists():
        raise FileNotFoundError(
            f'Input not found: {path}\n'
            'Run mortgage_rate_enrichment.py first, or check DATA_DIR.'
        )

    # low_memory=False scans the file before guessing mixed dtypes.
    df = pd.read_csv(path, low_memory=False)
    print(f'Original rows: {len(df):,}')
    print(f'Original columns: {df.shape[1]}')
    print('Column data types:\n', df.dtypes.to_string())

    missing = missing_summary(df)
    print('Missing-value summary (top 15):')
    print(missing.head(15).to_string(index=False))

    required = present_columns(df, DATE_FIELDS + NUMERIC_FIELDS + WEEK6_REQUIRED_FIELDS)
    missing_required = sorted(set(DATE_FIELDS + WEEK6_REQUIRED_FIELDS) - set(df.columns))
    print('Required fields found:', required)
    if missing_required:
        print('WARNING: required fields missing from this file:', missing_required)
    else:
        print('All handbook/Week 6 required fields are present.')
    return df, missing


def convert_dates(kind, df):
    print('\n' + '-' * 65)
    print(f'STEP 2: DATE CONVERSION ({kind})')
    print('-' * 65)

    date_report_rows = []
    for col in present_columns(df, DATE_FIELDS):
        raw_missing = int(df[col].isna().sum())
        # errors='coerce' turns unreadable strings into NaT instead of crashing.
        parsed = pd.to_datetime(df[col], errors='coerce')
        # Newly missing after parsing, excluding values that were already null.
        invalid = int((parsed.isna() & df[col].notna()).sum())
        df[col] = parsed
        print(
            f'{col}: raw missing={raw_missing:,}; '
            f'unparseable converted to NaT={invalid:,}; '
            f'total NaT after conversion={int(parsed.isna().sum()):,}'
        )
        date_report_rows.append({
            'dataset': kind,
            'column': col,
            'raw_missing': raw_missing,
            'unparseable_to_NaT': invalid,
            'total_NaT_after': int(parsed.isna().sum()),
        })
    return df, pd.DataFrame(date_report_rows)


def report_redundant_columns(kind, df):
    print('\n' + '-' * 65)
    print(f'STEP 3: REDUNDANT COLUMN REVIEW ({kind})')
    print('-' * 65)

    rows = []
    for col, reason in PROPOSED_REDUNDANT_COLUMNS.items():
        if col in df.columns:
            null_percent = 100 * df[col].isna().mean()
            print(f'PROPOSED DROP (not dropped): {col} | {null_percent:.1f}% missing | {reason}')
            rows.append({
                'dataset': kind,
                'column': col,
                'null_percent': null_percent,
                'reason': reason,
                'status': 'proposed_only_not_dropped',
            })

    approved_present = [col for col in APPROVED_COLUMNS_TO_DROP if col in df.columns]
    if approved_present:
        protected = set(WEEK6_REQUIRED_FIELDS + DATE_FIELDS + NUMERIC_FIELDS)
        unsafe = [col for col in approved_present if col in protected]
        if unsafe:
            raise ValueError(
                f'Refusing to drop Week 6 / handbook fields: {unsafe}'
            )
        print('Dropping approved columns only:', approved_present)
        df = df.drop(columns=approved_present)
    else:
        print('No columns dropped. APPROVED_COLUMNS_TO_DROP is empty.')
    return df, pd.DataFrame(rows)


def recommend_missing_handling(kind, missing_df):
    """Print recommended missing-value handling without filling analytic fields."""
    print('\n' + '-' * 65)
    print(f'STEP 4: MISSING-VALUE RECOMMENDATIONS ({kind})')
    print('-' * 65)

    recommendations = {
        'ClosePrice': 'Keep nulls. Do not fill with 0. Flag invalid non-null prices separately.',
        'ListPrice': 'Keep nulls. Do not fill with 0.',
        'OriginalListPrice': 'Keep nulls. Needed for close-to-original-list ratio; leave missing.',
        'LivingArea': 'Keep nulls. Do not fill with 0 because that would create fake PPSF values.',
        'DaysOnMarket': 'Keep nulls. Flag negative values; do not replace them.',
        'BedroomsTotal': 'Keep nulls. Flag negative counts only.',
        'BathroomsTotalInteger': 'Keep nulls. Flag negative counts only.',
        'Latitude': 'Keep nulls. Use missing_coordinate_flag. Never fill with 0.',
        'Longitude': 'Keep nulls. Use missing_coordinate_flag. Never fill with 0.',
        'CloseDate': 'Keep as NaT. Listings often have no close date yet.',
        'PurchaseContractDate': 'Keep as NaT. Compare only when present.',
        'ListingContractDate': 'Keep as NaT. Compare only when present.',
        'ContractStatusChangeDate': 'Keep as NaT. Not required for the timeline flags.',
        'rate_30yr_fixed': 'Keep unmatched mortgage rates as null. Do not fill with 0.',
        'year_month': 'Keep missing months as null if the source date was NaT.',
        'PostalCode': 'Keep as text. Do not convert missing zips to 0.',
        'City': 'Keep missing cities. Tableau filters can treat them as unknown.',
        'PropertySubType': 'Keep missing subtype. Do not invent a category.',
    }
    for _, row in missing_df.iterrows():
        col = row['column']
        if col in recommendations and row['null_count'] > 0:
            print(f"{col}: {row['null_count']:,} missing ({row['null_percent']:.2f}%). {recommendations[col]}")
    print('No missing prices, dates, coordinates, or mortgage rates were filled.')


def convert_and_flag_numeric(kind, df):
    print('\n' + '-' * 65)
    print(f'STEP 5: NUMERIC VALIDATION ({kind})')
    print('-' * 65)

    coerce_rows = []
    for col in present_columns(df, NUMERIC_FIELDS):
        before_na = int(df[col].isna().sum())
        # errors='coerce' turns non-numeric text into NaN.
        df[col] = pd.to_numeric(df[col], errors='coerce')
        after_na = int(df[col].isna().sum())
        newly_invalid = after_na - before_na
        print(f'{col}: newly invalid strings coerced to NaN={newly_invalid:,}')
        coerce_rows.append({
            'dataset': kind,
            'column': col,
            'newly_invalid_to_NaN': newly_invalid,
        })

    # Flag invalid values. Do not delete those rows.
    if 'ClosePrice' in df.columns:
        df['invalid_close_price_flag'] = df['ClosePrice'].notna() & (df['ClosePrice'] <= 0)
    if 'LivingArea' in df.columns:
        df['invalid_living_area_flag'] = df['LivingArea'].notna() & (df['LivingArea'] <= 0)
    if 'DaysOnMarket' in df.columns:
        df['negative_dom_flag'] = df['DaysOnMarket'].notna() & (df['DaysOnMarket'] < 0)
    if 'BedroomsTotal' in df.columns:
        df['negative_bedrooms_flag'] = df['BedroomsTotal'].notna() & (df['BedroomsTotal'] < 0)
    if 'BathroomsTotalInteger' in df.columns:
        df['negative_bathrooms_flag'] = df['BathroomsTotalInteger'].notna() & (df['BathroomsTotalInteger'] < 0)

    numeric_flag_cols = [
        'invalid_close_price_flag',
        'invalid_living_area_flag',
        'negative_dom_flag',
        'negative_bedrooms_flag',
        'negative_bathrooms_flag',
    ]
    flag_counts = {}
    for col in numeric_flag_cols:
        if col in df.columns:
            n_true = int(df[col].sum())
            flag_counts[col] = n_true
            print(f'{col} True count: {n_true:,} ({100 * n_true / len(df):.4f}%)')
    return df, pd.DataFrame(coerce_rows), flag_counts


def add_date_consistency_flags(kind, df):
    print('\n' + '-' * 65)
    print(f'STEP 6: DATE CONSISTENCY FLAGS ({kind})')
    print('-' * 65)

    listing = df['ListingContractDate'] if 'ListingContractDate' in df.columns else None
    purchase = df['PurchaseContractDate'] if 'PurchaseContractDate' in df.columns else None
    close = df['CloseDate'] if 'CloseDate' in df.columns else None

    if listing is not None and close is not None:
        comparable_listing_close = listing.notna() & close.notna()
        # True only when both dates exist and listing is after close.
        df['listing_after_close_flag'] = comparable_listing_close & (listing > close)
        print(f'Records with both ListingContractDate and CloseDate: {int(comparable_listing_close.sum()):,}')
        print(f'Records missing ListingContractDate or CloseDate: {int((~comparable_listing_close).sum()):,}')
    else:
        df['listing_after_close_flag'] = False
        comparable_listing_close = pd.Series(False, index=df.index)
        print('listing_after_close_flag skipped: required date columns are missing.')

    if purchase is not None and close is not None:
        comparable_purchase_close = purchase.notna() & close.notna()
        df['purchase_after_close_flag'] = comparable_purchase_close & (purchase > close)
        print(f'Records with both PurchaseContractDate and CloseDate: {int(comparable_purchase_close.sum()):,}')
        print(f'Records missing PurchaseContractDate or CloseDate: {int((~comparable_purchase_close).sum()):,}')
    else:
        df['purchase_after_close_flag'] = False
        comparable_purchase_close = pd.Series(False, index=df.index)
        print('purchase_after_close_flag skipped: required date columns are missing.')

    if listing is not None and purchase is not None:
        comparable_listing_purchase = listing.notna() & purchase.notna()
        # Handbook: PurchaseContractDate earlier than ListingContractDate.
        df['negative_timeline_flag'] = comparable_listing_purchase & (purchase < listing)
        print(f'Records with both ListingContractDate and PurchaseContractDate: {int(comparable_listing_purchase.sum()):,}')
        print(f'Records missing ListingContractDate or PurchaseContractDate: {int((~comparable_listing_purchase).sum()):,}')
    else:
        df['negative_timeline_flag'] = False
        print('negative_timeline_flag skipped: required date columns are missing.')

    date_flag_counts = {
        'listing_after_close_flag': int(df['listing_after_close_flag'].sum()),
        'purchase_after_close_flag': int(df['purchase_after_close_flag'].sum()),
        'negative_timeline_flag': int(df['negative_timeline_flag'].sum()),
    }
    for name, value in date_flag_counts.items():
        print(f'{name} True count: {value:,}')
    return df, date_flag_counts


def add_geographic_flags(kind, df):
    print('\n' + '-' * 65)
    print(f'STEP 7: GEOGRAPHIC DATA QUALITY ({kind})')
    print('-' * 65)
    print(
        'Using an approximate California bounding box, '
        f'lat {CA_LAT_MIN} to {CA_LAT_MAX}, '
        f'lon {CA_LON_MIN} to {CA_LON_MAX}. '
        'This is NOT a precise California state-boundary polygon.'
    )

    if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
        print('Latitude/Longitude missing from this dataset; geographic flags not created.')
        return df, {}

    lat = df['Latitude']
    lon = df['Longitude']
    has_both = lat.notna() & lon.notna()

    df['missing_coordinate_flag'] = lat.isna() | lon.isna()
    df['zero_coordinate_flag'] = (lat == 0) | (lon == 0)
    df['positive_longitude_flag'] = lon.notna() & (lon > 0)
    # World-range check: coordinates outside valid WGS84 extents.
    df['implausible_coordinate_flag'] = (
        (lat.notna() & ((lat < -90) | (lat > 90)))
        | (lon.notna() & ((lon < -180) | (lon > 180)))
    )
    # Approximate CA screening only where both coordinates exist.
    df['outside_ca_bbox_flag'] = has_both & (
        (lat < CA_LAT_MIN) | (lat > CA_LAT_MAX) | (lon < CA_LON_MIN) | (lon > CA_LON_MAX)
    )

    geo_flag_counts = {
        'missing_coordinate_flag': int(df['missing_coordinate_flag'].sum()),
        'zero_coordinate_flag': int(df['zero_coordinate_flag'].sum()),
        'positive_longitude_flag': int(df['positive_longitude_flag'].sum()),
        'implausible_coordinate_flag': int(df['implausible_coordinate_flag'].sum()),
        'outside_ca_bbox_flag': int(df['outside_ca_bbox_flag'].sum()),
    }
    for name, value in geo_flag_counts.items():
        print(f'{name} True count: {value:,}')
    print('Original Latitude and Longitude values were not changed.')
    return df, geo_flag_counts


def save_and_verify(kind, original_rows, df, output_path, date_cols):
    print('\n' + '-' * 65)
    print(f'STEP 8: SAVE AND VALIDATE {kind.upper()}')
    print('-' * 65)
    print(f'Rows before cleaning flags/conversions: {original_rows:,}')
    print(f'Rows after cleaning (should match): {len(df):,}')
    if len(df) != original_rows:
        raise ValueError(
            f'{kind}: row count changed from {original_rows} to {len(df)}. '
            'This script is not supposed to delete records.'
        )

    df.to_csv(output_path, index=False)
    print(f'Saved cleaned file (source files not overwritten): {output_path}')

    # CSV does not store pandas datetime dtypes. Reload a sample with parse_dates
    # to confirm the saved strings can be read back as dates.
    verify_dates = present_columns(df, date_cols)
    reloaded = pd.read_csv(output_path, nrows=20, parse_dates=verify_dates)
    print('Reloaded sample dtypes for date fields:')
    print(reloaded[verify_dates].dtypes.to_string())
    print('Cleaned dtypes for key analytic fields:')
    key_cols = present_columns(df, DATE_FIELDS + NUMERIC_FIELDS + WEEK6_REQUIRED_FIELDS)
    print(df[key_cols].dtypes.to_string())
    return output_path


def clean_one_dataset(kind, input_path, output_path):
    df, missing_before = inspect_dataset(kind, input_path)
    original_rows = len(df)
    original_cols = df.shape[1]

    df, date_report = convert_dates(kind, df)
    df, proposed_drops = report_redundant_columns(kind, df)
    recommend_missing_handling(kind, missing_before)
    df, coerce_report, numeric_flag_counts = convert_and_flag_numeric(kind, df)
    df, date_flag_counts = add_date_consistency_flags(kind, df)
    df, geo_flag_counts = add_geographic_flags(kind, df)

    missing_after = missing_summary(df)
    save_table(missing_before, REPORT_DIR / f'{kind}_missing_before.csv')
    save_table(missing_after, REPORT_DIR / f'{kind}_missing_after.csv')
    save_table(date_report, REPORT_DIR / f'{kind}_date_conversion_report.csv')
    save_table(proposed_drops, REPORT_DIR / f'{kind}_proposed_column_drops.csv')
    save_table(coerce_report, REPORT_DIR / f'{kind}_numeric_coercion_report.csv')

    save_and_verify(kind, original_rows, df, output_path, DATE_FIELDS)

    summary = {
        'dataset': kind,
        'rows_before': original_rows,
        'rows_after': len(df),
        'columns_before': original_cols,
        'columns_after': df.shape[1],
        'columns_dropped': original_cols - (df.shape[1] - (
            sum(col.endswith('_flag') for col in df.columns)
        )),
        **{f'date_{k}': v for k, v in date_flag_counts.items()},
        **{f'numeric_{k}': v for k, v in numeric_flag_counts.items()},
        **{f'geo_{k}': v for k, v in geo_flag_counts.items()},
    }
    return df, summary


def main():
    sold_df, sold_summary = clean_one_dataset('sold', SOLD_INPUT, SOLD_OUTPUT)
    listings_df, listings_summary = clean_one_dataset('listings', LISTINGS_INPUT, LISTINGS_OUTPUT)

    validation = pd.DataFrame([sold_summary, listings_summary])
    save_table(validation, REPORT_DIR / 'week4_5_validation_summary.csv')
    print('\n' + '=' * 65)
    print('WEEKS 4-5 VALIDATION SUMMARY')
    print('=' * 65)
    print(validation.to_string(index=False))
    print('\nFinished Weeks 4-5 cleaning.')
    print('Original combined and mortgage-enriched CSVs were not modified.')
    print('No rows were deleted. No unapproved columns were dropped.')


if __name__ == '__main__':
    main()
