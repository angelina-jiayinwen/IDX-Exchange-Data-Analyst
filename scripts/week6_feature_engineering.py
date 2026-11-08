#!/usr/bin/env python3
"""Week 6: cleaned CRMLS sold metrics, CDE district joins, and segments.

Run using /opt/anaconda3/bin/python. No network, raw MLS files, or Git writes.
Outputs go to outputs/private/week6; reruns use a new timestamped folder.
All original records survive. Source school fields are backed up as MLS_*.
ListingContractDate is interpreted as the listing agreement effective date
(RESO DD 2.1), not a substitute for DaysOnMarket or an on-market date.
"""
from pathlib import Path
from datetime import datetime
import argparse
import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import make_valid

DEFAULT_PROJECT = Path(__file__).resolve().parents[1]
DATES = ['CloseDate', 'ListingContractDate', 'PurchaseContractDate']
NUMBERS = ['ClosePrice', 'OriginalListPrice', 'LivingArea', 'DaysOnMarket',
           'Latitude', 'Longitude']
METRICS = ['PriceRatio', 'CloseToOriginalListRatio', 'PricePerSqFt',
           'DaysOnMarket', 'Year', 'Month', 'YrMo', 'ListingToContractDays',
           'ContractToCloseDays']
GROUPS = {'property_type': ['PropertyType', 'PropertySubType'],
          'geography': ['CountyOrParish', 'MLSAreaMajor'],
          'list_office': ['ListOfficeName'], 'buyer_office': ['BuyerOfficeName']}


def read_cleaned(path):
    """Keep identifiers and postal codes as text; never read a raw fallback."""
    if not path.is_file():
        raise FileNotFoundError(f'Required cleaned dataset missing: {path}')
    header = pd.read_csv(path, nrows=0).columns
    text = {c: 'string' for c in ['ListingKey', 'ListingId', 'PostalCode'] if c in header}
    return pd.read_csv(path, dtype=text, low_memory=False)


def inspect(kind, frame, path):
    print(f'\n{kind}: {path}\nRows={len(frame):,}; columns={len(frame.columns)}')
    print(frame.dtypes.to_string())
    relevant = [c for c in DATES + NUMBERS + ['year_month', 'rate_30yr_fixed'] if c in frame]
    print('Relevant missing counts:', frame[relevant].isna().sum().to_dict())
    if 'MlsStatus' in frame:
        print('Statuses:', frame.MlsStatus.value_counts(dropna=False).to_dict())


def engineer(df):
    """Coerce types, retain missing values, and distinguish invalid from missing."""
    quality, conversion = {}, {}
    for col in NUMBERS + DATES:
        raw = df[col]
        converted = (pd.to_datetime(raw, errors='coerce', format='mixed') if col in DATES
                     else pd.to_numeric(raw, errors='coerce'))
        bad = raw.notna() & converted.isna()
        if col in NUMBERS:
            bad |= converted.notna() & ~np.isfinite(converted)
            converted = converted.where(np.isfinite(converted))
        df[f'week6_invalid_source_{col}'] = bad
        conversion[col] = int(bad.sum())
        df[col] = converted

    for metric, denom in [('PriceRatio', 'OriginalListPrice'), ('PricePerSqFt', 'LivingArea')]:
        invalid = (df[f'week6_invalid_source_{denom}'] | df.week6_invalid_source_ClosePrice
                   | df[denom].le(0) | df.ClosePrice.le(0))
        good = df.ClosePrice.gt(0) & df[denom].gt(0) & ~invalid
        df[metric] = np.nan
        df.loc[good, metric] = df.loc[good, 'ClosePrice'] / df.loc[good, denom]
        df[f'week6_invalid_{metric}'] = invalid
        quality[metric] = int(invalid.sum())
    df['CloseToOriginalListRatio'] = df.PriceRatio.copy()
    quality['CloseToOriginalListRatio'] = quality['PriceRatio']

    # Keep the source DOM for review; summaries exclude invalid DOM.
    invalid_dom = df.week6_invalid_source_DaysOnMarket | df.DaysOnMarket.lt(0) | df.DaysOnMarket.mod(1).ne(0) & df.DaysOnMarket.notna()
    df['week6_invalid_DaysOnMarket'] = invalid_dom
    quality['DaysOnMarket'] = int(invalid_dom.sum())
    df['Year'] = df.CloseDate.dt.year.astype('Int64')
    df['Month'] = df.CloseDate.dt.month.astype('Int64')
    df['YrMo'] = df.CloseDate.dt.strftime('%Y-%m').astype('string')
    for col in ['Year', 'Month', 'YrMo']:
        quality[col] = conversion['CloseDate']

    print('\nListingContractDate: listing agreement effective date per RESO DD 2.1;')
    print('the requested interval measures agreement-to-accepted-offer days, not DOM.')
    for name, start, end in [('ListingToContractDays', 'ListingContractDate', 'PurchaseContractDate'),
                             ('ContractToCloseDays', 'PurchaseContractDate', 'CloseDate')]:
        df[name] = (df[end] - df[start]).dt.days.astype('Int64')
        invalid = df[name].lt(0).fillna(False) | df[f'week6_invalid_source_{start}'] | df[f'week6_invalid_source_{end}']
        df[f'week6_invalid_{name}'] = invalid
        # A review threshold, not a claim that lengthy valid transactions are errors.
        df[f'week6_long_{name}_review'] = df[name].gt(1095).fillna(False)
        quality[name] = int(invalid.sum())
    df['week6_listing_after_close'] = (df.ListingContractDate > df.CloseDate)
    df['week6_pre_2000_contract_date_review'] = (
        df.ListingContractDate.lt(pd.Timestamp('2000-01-01')) |
        df.PurchaseContractDate.lt(pd.Timestamp('2000-01-01')))
    print('Source conversion failures:', conversion)
    return quality, conversion


def enrich_districts(df, path):
    """Join by stable input row ID and district ID, never by MLS ListingKey."""
    if not path.is_file():
        raise FileNotFoundError(f'Missing school boundaries: {path}. Download the official '
                                '2024-25 CDE shapefile and extract all sidecars into school_districts/.')
    districts = gpd.read_file(path)
    print('\nDistrict boundary schema:', districts.dtypes.to_dict())
    print('District CRS:', districts.crs)
    print(districts[['CDCode', 'DistrictNa', 'DistrictTy']].head(10).to_string(index=False))
    print('District types:', districts.DistrictTy.value_counts(dropna=False).to_dict())
    if districts.crs is None:
        raise ValueError('District CRS absent; cannot safely infer it.')
    if districts.CDCode.isna().any() or districts.CDCode.duplicated().any():
        raise ValueError('District IDs must be nonmissing and unique.')
    if districts.geometry.isna().any() or districts.geometry.is_empty.any():
        raise ValueError('District file contains missing/empty geometry.')
    bad = ~districts.geometry.is_valid
    repaired = int(bad.sum())
    districts.loc[bad, 'geometry'] = districts.loc[bad, 'geometry'].map(make_valid)
    if not districts.geometry.is_valid.all() or districts.geometry.is_empty.any():
        raise ValueError('District geometry repair unsuccessful.')
    if not districts.geom_type.isin(['Polygon', 'MultiPolygon']).all():
        raise ValueError('Repair produced nonpolygon geometry; inspect boundaries.')
    print('Invalid district geometries repaired in memory:', repaired)

    valid = (df.Latitude.between(-90, 90) & df.Longitude.between(-180, 180)
             & df.Latitude.ne(0) & df.Longitude.ne(0))
    df['week6_valid_coordinates'] = valid
    points = gpd.GeoDataFrame({'week6_source_row_id': df.loc[valid, 'week6_source_row_id']},
                             geometry=gpd.points_from_xy(df.loc[valid, 'Longitude'], df.loc[valid, 'Latitude']),
                             crs='EPSG:4326').to_crs(districts.crs)
    any_match = pd.Series(False, index=df.index)
    any_ambiguous = pd.Series(False, index=df.index)
    stats = {'total_properties': len(df), 'valid_coordinates': int(valid.sum()),
             'repaired_district_geometries': repaired, 'district_crs': str(districts.crs)}
    for kind, field in [('Elementary', 'ElementarySchoolDistrict'),
                        ('High', 'HighSchoolDistrict'), ('Unified', 'UnifiedSchoolDistrict')]:
        subset = districts.loc[districts.DistrictTy.eq(kind), ['CDCode', 'DistrictNa', 'geometry']]
        if subset.empty:
            print(f'Unsupported district type: {kind}; no new field created.')
            continue
        if field in df:
            df[f'MLS_{field}'] = df[field].copy()
        # intersects includes exact boundary points; same-type ties remain ambiguous.
        joined = gpd.sjoin(points, subset, how='inner', predicate='intersects')
        pairs = joined.drop_duplicates(['week6_source_row_id', 'CDCode'])
        counts = pairs.groupby('week6_source_row_id').size()
        unique = pairs.loc[pairs.week6_source_row_id.map(counts).eq(1)].set_index('week6_source_row_id')
        df[field] = df.week6_source_row_id.map(unique.DistrictNa).astype('string')
        df[f'{kind}SchoolDistrictID'] = df.week6_source_row_id.map(unique.CDCode).astype('string')
        # Export every candidate for review, even when the authoritative field is null.
        candidates = pairs.groupby('week6_source_row_id').agg(
            names=('DistrictNa', lambda s: ' | '.join(sorted(s.astype(str)))),
            ids=('CDCode', lambda s: ' | '.join(sorted(s.astype(str)))))
        df[f'{kind}DistrictCandidates'] = df.week6_source_row_id.map(candidates.names).astype('string')
        df[f'{kind}DistrictCandidateIDs'] = df.week6_source_row_id.map(candidates.ids).astype('string')
        df[f'{kind}DistrictMatchCount'] = df.week6_source_row_id.map(counts).fillna(0).astype('Int64')
        ambiguous = df[f'{kind}DistrictMatchCount'].gt(1)
        df[f'{kind}DistrictAmbiguous'] = ambiguous
        any_match |= df[f'{kind}DistrictMatchCount'].gt(0)
        any_ambiguous |= ambiguous
        stats[f'{kind}_ambiguous_properties'] = int(ambiguous.sum())
        stats[f'{kind}_extra_matches'] = int((counts - 1).clip(lower=0).sum())
    df['week6_school_district_matched'] = any_match
    df['week6_school_district_ambiguous'] = any_ambiguous
    stats.update(matched_properties=int(any_match.sum()), unmatched_properties=int((~any_match).sum()),
                 ambiguous_properties=int(any_ambiguous.sum()),
                 match_percent_all=100 * float(any_match.mean()),
                 match_percent_valid=100 * int(any_match.sum()) / int(valid.sum()) if valid.any() else None)
    print('School district statistics:', json.dumps(stats, indent=2))
    return stats


def summaries(df):
    """Include null grouping keys and per-metric denominators; exclude invalid metrics."""
    work = df.copy()
    work['ClosePrice'] = work.ClosePrice.where(work.ClosePrice.gt(0))
    for col in ['DaysOnMarket', 'ListingToContractDays', 'ContractToCloseDays']:
        work[col] = work[col].mask(work[f'week6_invalid_{col}'])
    stats = {'MeanClosePrice': ('ClosePrice', 'mean'), 'MedianClosePrice': ('ClosePrice', 'median'),
             'MedianPricePerSqFt': ('PricePerSqFt', 'median'), 'MeanPriceRatio': ('PriceRatio', 'mean'),
             'MedianDaysOnMarket': ('DaysOnMarket', 'median'),
             'MeanListingToContractDays': ('ListingToContractDays', 'mean'),
             'MeanContractToCloseDays': ('ContractToCloseDays', 'mean')}
    result = {}
    for label, requested in GROUPS.items():
        keys = [c for c in requested if c in work]
        if not keys:
            raise KeyError(f'No supported grouping fields for {label}: {requested}')
        aggregation = {'TransactionCount': ('week6_source_row_id', 'size'), **stats}
        for source in sorted({source for source, _ in stats.values()}):
            aggregation[f'{source}ValidCount'] = (source, 'count')
        table = work.groupby(keys, dropna=False).agg(**aggregation).reset_index()
        table['SmallGroupFlag'] = table.TransactionCount.lt(10)
        table = table.sort_values('TransactionCount', ascending=False, kind='stable')
        if int(table.TransactionCount.sum()) != len(df):
            raise AssertionError(f'{label} counts do not reconcile.')
        result[label] = table
    return result


def validate(df, original, tables):
    """Full-dataset checks, including original attributes and all valid calculations."""
    assert len(df) == len(original)
    assert np.array_equal(df.week6_source_row_id, np.arange(len(original)))
    assert df.PriceRatio.equals(df.CloseToOriginalListRatio)
    for metric, denominator in [('PriceRatio', 'OriginalListPrice'), ('PricePerSqFt', 'LivingArea')]:
        good = df.ClosePrice.gt(0) & df[denominator].gt(0)
        np.testing.assert_allclose(df.loc[good, metric], df.loc[good, 'ClosePrice'] / df.loc[good, denominator])
        assert df.loc[~good, metric].isna().all()
    for col, start, end in [('ListingToContractDays', 'ListingContractDate', 'PurchaseContractDate'),
                            ('ContractToCloseDays', 'PurchaseContractDate', 'CloseDate')]:
        pd.testing.assert_series_equal(df[col], (df[end]-df[start]).dt.days.astype('Int64'), check_names=False)
    assert df.YrMo.equals(df.CloseDate.dt.strftime('%Y-%m').astype('string').rename('YrMo'))
    assert df.Year.equals(df.CloseDate.dt.year.astype('Int64').rename('Year'))
    assert df.Month.equals(df.CloseDate.dt.month.astype('Int64').rename('Month'))
    assert df.CloseDate.between('2024-01-01', '2026-09-30').all()
    assert original.MlsStatus.eq('Closed').all()
    for col in original:
        if col in NUMBERS + DATES:
            continue
        preserved = f'MLS_{col}' if f'MLS_{col}' in df else col
        pd.testing.assert_series_equal(original[col], df[preserved], check_names=False)
    assert all(int(t.TransactionCount.sum()) == len(original) for t in tables.values())
    print('\nPASS: full-dataset price formulas, duplicate ratios, day intervals, date parts,')
    print('date coverage, preserved source attributes/mortgage rates, row identity, and four segment totals.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, default=DEFAULT_PROJECT)
    args = parser.parse_args()
    project = args.project_dir.resolve()
    data = project / 'CRMLS data'
    sold_path = data / 'CRMLSSoldCombined_202401_202609_cleaned.csv'
    listings_path = data / 'CRMLSListingCombined_202401_202609_cleaned.csv'
    print('Python:', sys.version, '\nExecutable:', sys.executable)
    print('Versions:', {'pandas': pd.__version__, 'numpy': np.__version__, 'geopandas': gpd.__version__})
    sold, listings = read_cleaned(sold_path), read_cleaned(listings_path)
    inspect('CLEANED SOLD', sold, sold_path)
    inspect('CLEANED LISTINGS', listings, listings_path)
    required = NUMBERS + DATES
    missing = [c for c in required if c not in sold]
    if missing:
        raise KeyError(f'Required sold source fields absent: {missing}')
    for c in ['year_month', 'rate_30yr_fixed']:
        if c not in sold:
            print(f'WARNING: mortgage enrichment column absent: {c}')
    print('\nLISTINGS APPLICABILITY: this file contains mixed statuses, not just active listings.')
    print('DOM and coordinate-based districts are applicable. Agreement-to-contract days require both dates.')
    print('Sold metrics require confirmed Closed status plus valid ClosePrice/CloseDate and denominators.')
    print('Existing listings mortgage month uses ListingContractDate; no listings file is modified.')
    del listings
    original = sold.copy()
    sold['week6_source_row_id'] = np.arange(len(sold))
    sold['week6_duplicate_listing_key'] = sold.ListingKey.duplicated(keep=False)
    print('Repeated ListingKeys (beyond first):', int(sold.ListingKey.duplicated().sum()))
    quality, conversion = engineer(sold)
    geo = enrich_districts(sold, project / 'school_districts' / 'DistrictAreas2425.shp')
    tables = summaries(sold)
    validate(sold, original, tables)
    metric_report = pd.DataFrame([{'metric': c, 'dtype': str(sold[c].dtype),
                                   'missing_count': int(sold[c].isna().sum()),
                                   'invalid_count': quality[c]} for c in METRICS])
    print('\nINPUT/OUTPUT ROWS:', len(original), len(sold))
    print('\nENGINEERED METRIC QUALITY\n', metric_report.to_string(index=False))
    print('\nNEW COLUMNS / DTYPES / MISSING COUNTS')
    new = [c for c in sold if c not in original]
    print(pd.DataFrame({'dtype': sold[new].dtypes.astype(str), 'missing': sold[new].isna().sum()}).to_string())
    sample_cols = [c for c in ['week6_source_row_id', 'ListingKey'] + NUMBERS + DATES + METRICS +
                   ['ElementarySchoolDistrict', 'HighSchoolDistrict', 'UnifiedSchoolDistrict',
                    'week6_school_district_ambiguous', 'rate_30yr_fixed'] if c in sold]
    sample_cols = list(dict.fromkeys(sample_cols))
    # Deterministic selection distributed across the entire input period.
    sample = sold.iloc[np.linspace(0, len(sold)-1, min(20, len(sold)), dtype=int)][sample_cols]
    print('\nSAMPLE PROPERTIES\n', sample.head(10).to_string(index=False))
    print('\nSAMPLE PROPERTY SUMMARY\n', tables['property_type'].head(10).to_string(index=False))

    base = project / 'outputs' / 'private' / 'week6'
    names = ['week6_sold_enriched.csv', 'week6_feature_sample.csv', 'week6_metric_quality.csv',
             'week6_validation.json', 'week6_validation_report.txt'] + [f'week6_summary_{k}.csv' for k in GROUPS]
    out = base
    if any((out / n).exists() for n in names):
        out = base / ('run_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    out.mkdir(parents=True, exist_ok=True)
    sold.to_csv(out / names[0], index=False, mode='x')
    sample.to_csv(out / names[1], index=False, mode='x')
    metric_report.to_csv(out / 'week6_metric_quality.csv', index=False, mode='x')
    for key, table in tables.items():
        table.to_csv(out / f'week6_summary_{key}.csv', index=False, mode='x')
    report = {'checks': 'PASS', 'input_rows': len(original), 'output_rows': len(sold),
              'input_sold': str(sold_path), 'input_listings': str(listings_path),
              'boundary_file': str(project / 'school_districts/DistrictAreas2425.shp'),
              'geography': geo, 'source_conversion_invalid_counts': conversion,
              'metric_quality': metric_report.to_dict(orient='records'),
              'duplicate_listing_keys_beyond_first': int(original.ListingKey.duplicated().sum()),
              'pre_2000_contract_date_review': int(sold.week6_pre_2000_contract_date_review.sum()),
              'long_interval_review_counts': {c: int(sold[c].sum()) for c in sold if c.startswith('week6_long_')},
              'segment_count_totals': {k: int(t.TransactionCount.sum()) for k, t in tables.items()},
              'new_columns': new,
              'assumptions': ['2024-25 district boundaries applied to the entire 2024-2026 period; not historical attendance guarantees.',
                              'Same-type ambiguous districts have null authoritative names and all candidate names/IDs retained.',
                              'Boundary points count as intersections; no nearest matching.',
                              'Invalid negative intervals/DOM preserved in detail, excluded from summaries.',
                              'Positive intervals over 1095 days flagged for review, retained in summaries.',
                              'TransactionCount counts original closed records including repeated ListingKeys.']}
    with (out / 'week6_validation.json').open('x') as handle:
        json.dump(report, handle, indent=2)
    with (out / 'week6_validation_report.txt').open('x') as handle:
        handle.write(json.dumps(report, indent=2) + '\n\n' + metric_report.to_string(index=False)
                     + '\n\nSAMPLE PROPERTIES\n' + sample.head(10).to_string(index=False)
                     + '\n\nPROPERTY SUMMARY\n' + tables['property_type'].head(10).to_string(index=False))
    print('\nOUTPUT DIRECTORY:', out)
    print('All checks passed before export. Prior files, README, .gitignore, and Git were preserved.')


if __name__ == '__main__':
    main()
