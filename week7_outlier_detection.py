#!/usr/bin/env python3
"""Week 7: flag outliers in the cleaned CRMLS sold and listings datasets."""

import csv
from datetime import datetime
from hashlib import file_digest
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter


PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / 'outputs' / 'private' / 'week7'
SOURCES = {
    'sold': 'CRMLSSoldCombined_202401_202609_cleaned.csv',
    'listings': 'CRMLSListingCombined_202401_202609_cleaned.csv',
}
NUMERIC_COLUMNS = ['ClosePrice', 'ListPrice', 'LivingArea', 'DaysOnMarket']
ID_COLUMNS = ['ListingId', 'ListingKey']


def analyze(kind, source, output, comparison_source=None):
    with source.open('rb') as original:
        source_hash = file_digest(original, 'sha256').hexdigest()

    # Load just the fields needed for analysis. The export streams the full records.
    fields = pd.read_csv(source, nrows=0).columns
    relevant = [c for c in NUMERIC_COLUMNS + ['MlsStatus'] + ID_COLUMNS if c in fields]
    if not relevant:
        relevant = [fields[0]]  # Keep the row count even if every metric is absent.
    data = pd.read_csv(source, usecols=relevant, dtype=str, keep_default_na=False)
    total = len(data)
    if not total:
        raise ValueError(f'No data rows in {source}')

    all_rows = pd.Series(True, index=data.index)
    sale_rows = all_rows
    notes = []
    if kind == 'listings':
        if 'MlsStatus' in data:
            sale_rows = data['MlsStatus'].str.strip().str.casefold().eq('closed')
            notes.append(f'Sale metrics apply to the {sale_rows.sum():,} Closed rows.')
            if 'ClosePrice' in data:
                other_prices = (~sale_rows & data['ClosePrice'].str.strip().ne('')).sum()
                notes.append(f'Populated ClosePrice outside Closed status: {other_prices:,}. '
                             'These values are outside the sale metrics and validation scope.')
        else:
            sale_rows = ~all_rows
            notes.append('Sale metrics skipped because MlsStatus is absent.')

    values, flags, quality = {}, {}, []
    invalid_row = ~all_rows
    missing_row = ~all_rows
    for column in NUMERIC_COLUMNS:
        eligible = sale_rows if column == 'ClosePrice' else all_rows
        if column not in data:
            notes.append(f'Source column unavailable: {column}.')
            continue
        if column == 'ClosePrice' and not eligible.any():
            continue

        raw = data[column].str.strip()
        number = pd.to_numeric(raw, errors='coerce')
        missing = eligible & raw.eq('')
        bad_number = eligible & ~missing & ~np.isfinite(number)
        if column == 'DaysOnMarket':
            bad_range = eligible & np.isfinite(number) & number.lt(0)
        else:
            bad_range = eligible & np.isfinite(number) & number.le(0)
        invalid = bad_number | bad_range
        values[column] = number.where(eligible & ~missing & ~invalid)
        flags[f'week7_missing_{column}'] = missing
        flags[f'week7_invalid_{column}'] = invalid
        invalid_row |= invalid
        missing_row |= missing
        quality.append((column, int(eligible.sum()), int(missing.sum()),
                        int(bad_number.sum()), int(bad_range.sum())))

    price = 'ClosePrice' if kind == 'sold' else 'ListPrice'
    derived = {}
    for name, numerator, denominator in [
        ('week7_price_per_sqft', price, 'LivingArea'),
        ('week7_close_list_ratio', 'ClosePrice', 'ListPrice'),
    ]:
        if numerator in values and denominator in values:
            # Invalid, zero, and missing inputs were masked before division.
            ratio = values[numerator] / values[denominator]
            overflow = ratio.notna() & ~np.isfinite(ratio)
            if overflow.any():
                flags[f'{name}_nonfinite'] = overflow
                invalid_row |= overflow
                notes.append(f'{name} overflowed on {overflow.sum():,} rows.')
            derived[name] = ratio.where(np.isfinite(ratio))

    metrics = {
        'Sale price ($)': ('is_price_outlier', values.get('ClosePrice')),
        'Price per sq ft ($)': ('is_price_per_sqft_outlier', derived.get('week7_price_per_sqft')),
        'Close-to-list ratio': ('is_close_list_ratio_outlier', derived.get('week7_close_list_ratio')),
        'Days on market': ('is_dom_outlier', values.get('DaysOnMarket')),
        'Living area (sq ft)': ('is_living_area_outlier', values.get('LivingArea')),
    }
    if kind == 'listings':
        metrics['List price ($)'] = ('is_list_price_outlier', values.get('ListPrice'))

    any_outlier = ~all_rows
    thresholds = []
    evaluated = {}
    for label, (flag, series) in metrics.items():
        if series is None or not series.notna().any():
            notes.append(f'IQR and market statistics skipped for {label}: no usable values.')
            continue
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        low = series.lt(lower)
        high = series.gt(upper)
        flags[flag] = low | high
        any_outlier |= flags[flag]
        count = int(flags[flag].sum())
        thresholds.append((label, int(series.count()), q1, q3, iqr, lower, upper,
                           int(low.sum()), int(high.sum()), count, 100 * count / total))
        evaluated[label] = (series, upper)
        if iqr == 0:
            notes.append(f'{label} has zero IQR. Values outside its collapsed fences are flagged.')

    flags['is_any_outlier'] = any_outlier
    flags['is_business_rule_invalid'] = invalid_row
    flags['is_missing_metric_input'] = missing_row
    keep = ~(any_outlier | invalid_row)
    retained = int(keep.sum())

    added = pd.DataFrame({**derived, **flags}).fillna('')
    write_outputs(source, output, kind, added, keep)
    validate_exports(source, output, kind, added, keep)
    with source.open('rb') as original:
        if file_digest(original, 'sha256').hexdigest() != source_hash:
            raise ValueError(f'{kind}: cleaned input changed during the run')

    metric_flags = [metrics[label][0] for label in evaluated]
    overlap = added[metric_flags].sum(axis='columns').gt(1).sum()

    impact = []
    plots = {}
    plot_metrics = {
        'Sale price ($)' if kind == 'sold' else 'List price ($)': 'price',
        'Price per sq ft ($)': 'price_per_sqft',
        'Days on market': 'days_on_market',
    }
    for label, (series, upper) in evaluated.items():
        before = series.dropna()
        after = series[keep].dropna()
        impact.append((label, len(before), before.mean(), before.median(),
                       len(after), after.mean(), after.median()))
        if label in plot_metrics:
            plots[plot_metrics[label]] = (label, before, after, upper)

    lines = [
        kind.upper(), '=' * 72,
        f'Source: {source.relative_to(PROJECT)}',
        f'Original rows: {total:,}',
        f'Filtered rows: {retained:,}',
        f'Removed rows: {total - retained:,} ({100 * (total - retained) / total:.2f}%)',
        f'Rows with any IQR outlier: {any_outlier.sum():,}',
        f'Rows flagged by more than one IQR metric: {overlap:,}',
        f'Rows with business-rule violations: {invalid_row.sum():,}',
        f'Rows with both: {(any_outlier & invalid_row).sum():,}',
        f'Removed by IQR flags alone: {(any_outlier & ~invalid_row).sum():,}',
        f'Removed by business rules alone: {(invalid_row & ~any_outlier).sum():,}',
        f'Rows with missing metric inputs: {missing_row.sum():,}',
        f'Rows retained with missing metric inputs: {(missing_row & keep).sum():,}',
        '',
        'IQR STATISTICS',
        'Flagged % uses all original rows. Evaluated counts usable values for each metric.',
        format_table(
            thresholds, ['Metric', 'Evaluated', 'Q1', 'Q3', 'IQR', 'Lower fence',
                         'Upper fence', 'Below', 'Above', 'Flagged', 'Flagged %']),
        '',
        'SOURCE VALUE QUALITY',
        'Invalid range means price or area <= 0, or days on market < 0.',
        'An invalid or missing divisor prevents calculation of its derived metric.',
        format_table(
            quality, ['Field', 'In scope', 'Missing', 'Nonnumeric/nonfinite', 'Invalid range']),
        '',
        'MARKET STATISTICS',
        'Before and after summaries use the valid observations for each metric.',
        format_table(
            impact, ['Metric', 'Before N', 'Before mean', 'Before median', 'After N',
                     'After mean', 'After median']),
    ]
    if 'Close-to-list ratio' in evaluated:
        lines += ['', *review_ratios(derived['week7_close_list_ratio'], values, data,
                                     comparison_source)]
    if notes:
        lines += ['', 'DATASET NOTES', *notes]
    lines += [
        '',
        'POST-EXPORT VALIDATION: PASSED',
        'All flagged rows match the input records in order, with the expected Week 7 values.',
        'The filtered file matches the retained rows exactly and has no removal flags.',
        'Validation uses the flags from the original input thresholds.',
        f'Cleaned input SHA-256 matched before and after export: {source_hash}',
    ]
    print(f'{kind}: {total:,} input rows, {retained:,} filtered rows')
    return '\n'.join(lines), plots


def review_ratios(ratios, values, data, comparison_source):
    # Review the upper tail of the original valid ratios without changing any flags.
    valid = ratios.dropna()
    low, p99, p999, high = valid.quantile([0, 0.99, 0.999, 1])
    highest = valid.nlargest(20)
    top = data.loc[highest.index, [c for c in ID_COLUMNS if c in data]].copy()
    top['ClosePrice ($)'] = values['ClosePrice'].loc[highest.index]
    top['ListPrice ($)'] = values['ListPrice'].loc[highest.index]
    top['Ratio'] = highest
    top.index = range(1, len(top) + 1)
    top.index.name = 'Rank'
    prices = top['ListPrice ($)']
    small_prices = prices.nsmallest(min(3, len(prices)))
    small_prices_text = ', '.join(f'${price:,.2f}' for price in small_prices)
    exact_thousand = highest.eq(1000).sum()
    huge_closes = top['ClosePrice ($)'].ge(100_000_000).sum()
    rest = valid.drop(index=highest.index)
    lines = [
        'EXTREME CLOSE-TO-LIST RATIOS',
        f'Valid ratios: {len(valid):,}. Minimum: {low:.10g}. Maximum: {high:,.4f}.',
        f'99th percentile: {p99:,.6f}. 99.9th percentile: {p999:,.6f}.',
        f'Highest {len(highest)} valid ratios, in descending order (ties follow input order)',
        top.to_string(na_rep='n/a', float_format='{:,.4f}'.format),
        '',
        'Observed values',
        f"The highest ratio pairs a ${top.iloc[0]['ClosePrice ($)']:,.2f} close with a "
        f"${top.iloc[0]['ListPrice ($)']:,.2f} list price. The lowest list prices "
        f'in the table are {small_prices_text}.',
        f'Among these rows, {exact_thousand:,} ratios equal 1,000 exactly and '
        f'{huge_closes:,} close prices are at least $100 million.',
    ]
    if not rest.empty:
        lines.append(f'For sensitivity only, the mean is {rest.mean():,.6f} when the '
                     f'highest {len(highest)} ratios are omitted, versus {valid.mean():,.6f} overall.')
    # Compare top records to the other cleaned file when a shared MLS key is available.
    if comparison_source is not None and 'ListingKey' in top:
        columns = ['ListingKey', 'MlsStatus', 'ListPrice', 'ClosePrice']
        if set(columns).issubset(pd.read_csv(comparison_source, nrows=0).columns):
            other = pd.read_csv(comparison_source, usecols=columns, dtype=str)
            other = other.loc[other['ListingKey'].isin(top['ListingKey']) &
                              other['MlsStatus'].str.strip().str.casefold().eq('closed')].copy()
            other['ListPrice ($)'] = pd.to_numeric(other['ListPrice'], errors='coerce')
            other['Other close ($)'] = pd.to_numeric(other['ClosePrice'], errors='coerce')
            matched = top.merge(other, on=['ListingKey', 'ListPrice ($)'])
            differences = matched.loc[matched['Other close ($)'].gt(0) &
                                      matched['Other close ($)'].ne(matched['ClosePrice ($)']),
                                      ['ListingKey', 'ListPrice ($)', 'ClosePrice ($)',
                                       'Other close ($)']].drop_duplicates()
            if not differences.empty:
                lines += ['Closed records with the same MLS key and list price but different closes:',
                          differences.to_string(index=False, float_format='{:,.2f}'.format)]
    lines += [
        'Possible explanations',
        'Very small list prices could be placeholders or entry errors. Large closing',
        'prices and ratios near 1,000 could reflect misplaced digits or a scale mismatch.',
        'The cleaned MLS files alone cannot establish the intended prices. The review',
        'does not change the IQR fences, business rules, or CSV exports.',
    ]
    return lines


def format_table(rows, headers):
    if not rows:
        return 'No rows to report.'
    table = pd.DataFrame(rows, columns=headers)
    formats = {}
    for column in table:
        if pd.api.types.is_integer_dtype(table[column]):
            formats[column] = '{:,}'.format
        elif pd.api.types.is_float_dtype(table[column]):
            formats[column] = '{:,.4f}'.format
    return table.to_string(index=False, na_rep='n/a', formatters=formats)


def write_outputs(source, output, kind, added, keep):
    flagged = output / f'week7_{kind}_flagged.csv'
    filtered = output / f'week7_{kind}_filtered.csv'
    # Preserve CSV field values exactly, including identifiers and decimal strings.
    with (source.open(encoding='utf-8-sig', newline='') as original,
          flagged.open('x', encoding='utf-8', newline='') as all_file,
          filtered.open('x', encoding='utf-8', newline='') as filtered_file):
        reader = csv.reader(original)
        header = next(reader)
        conflicts = set(header).intersection(added.columns)
        if conflicts:
            raise ValueError(f'Week 7 output names already in source: {sorted(conflicts)}')
        all_rows = csv.writer(all_file)
        kept_rows = csv.writer(filtered_file)
        all_rows.writerow(header + list(added.columns))
        kept_rows.writerow(header + list(added.columns))
        records = (row for row in reader if row)
        for row, new_fields, retain in zip(
                records, added.itertuples(index=False, name=None), keep, strict=True):
            combined = row + list(new_fields)
            all_rows.writerow(combined)
            if retain:
                kept_rows.writerow(combined)


def validate_exports(source, output, kind, added, keep):
    flagged = output / f'week7_{kind}_flagged.csv'
    filtered = output / f'week7_{kind}_filtered.csv'
    # Read the exports back in order. This preserves legitimate repeated MLS records.
    with (source.open(encoding='utf-8-sig', newline='') as original,
          flagged.open(encoding='utf-8', newline='') as all_file,
          filtered.open(encoding='utf-8', newline='') as filtered_file):
        source_rows = csv.reader(original)
        flagged_rows = csv.reader(all_file)
        filtered_rows = csv.reader(filtered_file)
        header = next(source_rows) + list(added.columns)
        if next(flagged_rows, None) != header or next(filtered_rows, None) != header:
            raise ValueError(f'{kind}: export headers differ from the expected columns')
        outlier_col = header.index('is_any_outlier')
        invalid_col = header.index('is_business_rule_invalid')
        records = (row for row in source_rows if row)
        expected_fields = added.itertuples(index=False, name=None)
        for row_number, (row, fields, actual, retain) in enumerate(
                zip(records, expected_fields, flagged_rows, keep, strict=True), start=1):
            if actual != row + list(map(str, fields)):
                raise ValueError(f'{kind}: flagged export differs at data row {row_number}')
            if retain:
                if actual[outlier_col] != 'False' or actual[invalid_col] != 'False':
                    raise ValueError(f'{kind}: retained a removal flag at data row {row_number}')
                if next(filtered_rows, None) != actual:
                    raise ValueError(f'{kind}: filtered export differs at source row {row_number}')
        if next(filtered_rows, None) is not None:
            raise ValueError(f'{kind}: filtered export contains extra records')


def save_plots(results, output):
    plot_dir = output / 'plots'
    plot_dir.mkdir()
    for name, title in [
        ('price', 'Price before and after filtering'),
        ('price_per_sqft', 'Price per square foot before and after filtering'),
        ('days_on_market', 'Days on market before and after filtering'),
    ]:
        panels = [(kind, plots[name]) for kind, plots in results.items() if name in plots]
        if not panels:
            continue
        fig, axes = plt.subplots(1, len(panels), figsize=(5.4 * len(panels), 4.5),
                                 squeeze=False, layout='constrained')
        fig.suptitle(title, fontsize=15)
        for ax, (kind, (label, before, after, upper)) in zip(axes[0], panels):
            ax.set_title(kind.capitalize())
            if name == 'days_on_market':
                # A shared displayed range makes the central distributions readable.
                limit = max(1, upper)
                bins = np.linspace(0, limit, 26)
                for series, color, phase in [(before, '#285b8f', 'Before'),
                                              (after, '#17755e', 'After')]:
                    if not series.empty:
                        shown = series[series.le(limit)]
                        omitted = len(series) - len(shown)
                        ax.hist(shown, bins=bins, weights=np.full(len(shown), 100 / len(series)),
                                histtype='step', linewidth=1.8, color=color,
                                label=f'{phase} ({omitted:,} above range)')
                ax.set_xlim(0, limit)
                ax.set_xlabel(label)
                ax.set_ylabel('% of valid values per bin')
                ax.legend(frameon=False, fontsize=8)
            else:
                ax.boxplot([before, after], tick_labels=[f'Before\nn = {len(before):,}',
                                                          f'After\nn = {len(after):,}'],
                           showfliers=False, patch_artist=True,
                           boxprops={'facecolor': '#d8e7f3', 'edgecolor': '#285b8f'},
                           medianprops={'color': '#852e24', 'linewidth': 1.8})
                ax.set_ylabel(label)
                ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
                ax.set_xlabel('Points beyond boxplot whiskers omitted', fontsize=9)
            ax.grid(axis='y', alpha=0.25)
        fig.savefig(plot_dir / f'week7_{name}.png', dpi=150)
        plt.close(fig)


def main():
    sources = {kind: PROJECT / 'CRMLS data' / name for kind, name in SOURCES.items()}
    missing = [path for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError('Missing cleaned input(s): ' + ', '.join(map(str, missing)))

    try:
        OUTPUT.mkdir(parents=True)
        output = OUTPUT
    except FileExistsError:
        output = OUTPUT / datetime.now().strftime('run_%Y%m%d_%H%M%S_%f')
        output.mkdir()

    sections = [
        'IDX EXCHANGE | WEEK 7 OUTLIER DETECTION AND DATA QUALITY',
        'Coverage: January 2024 through September 2026, Residential CRMLS records.',
        '',
        'METHOD',
        'Thresholds use each dataset\'s own valid values for each metric. Flags mark values',
        'strictly outside Q1 - 1.5 × IQR and Q3 + 1.5 × IQR. A statistical flag identifies',
        'a value for review. It can capture legitimate luxury homes or long market times.',
        'Filtered CSVs exclude any IQR flag or confirmed rule violation. Missing values',
        'alone allow retention. Thresholds are fitted once, before filtering.',
        'Price per sq ft uses ClosePrice for sold and ListPrice for listings. LivingArea',
        'is assumed to be interior square feet. The inputs lack a living-area unit column.',
        'Close-to-list uses ClosePrice divided by ListPrice. Week 6 used OriginalListPrice',
        'for its ratio. Week 7 uses the paired cleaned inputs and derives its own metrics.',
        'The listings source covers multiple statuses. Listing metrics use all statuses,',
        'with a Closed subset for sale price and close-to-list ratio. Counts are records.',
    ]
    results = {}
    for kind, source in sources.items():
        other_kind = 'listings' if kind == 'sold' else 'sold'
        report, results[kind] = analyze(kind, source, output, sources[other_kind])
        sections.extend(['', report])
    save_plots(results, output)
    (output / 'week7_outlier_report.txt').write_text('\n'.join(sections) + '\n', encoding='utf-8')
    print(f'Week 7 outputs: {output}')


if __name__ == '__main__':
    main()
