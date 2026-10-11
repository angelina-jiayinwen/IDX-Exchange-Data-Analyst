
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Save plots without requiring a graphical window.
import matplotlib.pyplot as plt

INPUTS = {
    'sold': Path('/Users/angelinawen/Desktop/CRMLS data/CRMLSSoldCombined_202401_202609.csv'),
    'listings': Path('/Users/angelinawen/Desktop/CRMLS data/CRMLSListingCombined_202401_202609.csv'),
}
OUTPUT_ROOT = Path('outputs/private')
NUMERIC_FIELDS = [
    'ClosePrice', 'ListPrice', 'OriginalListPrice', 'LivingArea',
    'LotSizeAcres', 'BedroomsTotal', 'BathroomsTotalInteger',
    'DaysOnMarket', 'YearBuilt',
]
CORE_FIELDS = {
    'ListingKey', 'ListingId', 'PropertyType', 'PropertySubType',
    'ClosePrice', 'ListPrice', 'OriginalListPrice', 'LivingArea',
    'LotSizeAcres', 'BedroomsTotal', 'BathroomsTotalInteger',
    'DaysOnMarket', 'YearBuilt', 'CloseDate', 'ListingContractDate',
    'PurchaseContractDate', 'ContractStatusChangeDate', 'CountyOrParish',
    'City', 'PostalCode', 'MLSAreaMajor', 'Latitude', 'Longitude',
    'ListAgentFullName', 'ListOfficeName', 'BuyerOfficeName',
}
PERCENTILES = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]


def save_table(df, path, index=True):
    df.to_csv(path, index=index)
    print(f'Saved: {path}')


def analyze_dataset(kind, path):
    print(f'\n{"=" * 65}\n{kind.upper()} DATASET\n{"=" * 65}')
    if not path.exists():
        raise FileNotFoundError(
        f'Input not found: {path}\n'
        'Check the path to your Week 1 Residential-filtered CSV.'
    )
    out = OUTPUT_ROOT / kind
    plots = out / 'plots'
    plots.mkdir(parents=True, exist_ok=True)

    # 1. Inspect Residential-filtered combined data.
    df_all = pd.read_csv(path, low_memory=False)
    print('Original rows, columns:', df_all.shape)
    print('First five rows:\n', df_all.head().to_string())
    print('Column names:\n', df_all.columns.tolist())
    print('Column data types:\n', df_all.dtypes.to_string())
    structure = pd.DataFrame({
        'column': df_all.columns,
        'dtype': df_all.dtypes.astype(str).values,
    })
    save_table(structure, out / 'column_structure.csv', index=False)
    
    # 2. Validate PropertyType
    # ----------------------------------------------------------

    # Residential filtering was completed in Week 1.
    # Both combined datasets contain Residential properties only.

    # Count unique property types
    types = df_all['PropertyType'].value_counts(dropna=False)

    print("Property types in dataset:")
    print(types)

    # Save property type summary
    type_report = pd.DataFrame({
    'PropertyType': types.index,
    'count': types.values,
    'percent': types.values / len(df_all) * 100
})

    save_table(
    type_report,
    out / 'property_type_summary.csv',
    index=False
)

    # ----------------------------------------------------------
    # 3. Validate Residential filtering
    # ----------------------------------------------------------

    # No additional filtering needed.
    df = df_all.copy()

    # Verify all records are Residential
    assert df['PropertyType'].eq('Residential').all(), \
    "Dataset contains non-Residential properties!"

    print("Residential filtering verified.")
    print("Total Residential records:", len(df))
    print("Unique property types:", df['PropertyType'].unique())

    # 4. Missingness and suggested retention decisions (not actual deletion).
    missing = pd.DataFrame({
        'column': df.columns,
        'null_count': df.isna().sum().values,
        'null_percent': (df.isna().mean() * 100).values,
    }).sort_values('null_percent', ascending=False)
    missing['over_90_percent'] = missing['null_percent'] > 90
    missing['decision'] = missing.apply(
        lambda row: 'Retain: core/future-use field' if row['column'] in CORE_FIELDS
        else ('Review for dropping (not deleted)' if row['over_90_percent']
              else 'Retain pending review'),
        axis=1,
    )
    print('Missing value report:\n', missing.to_string(index=False))
    save_table(missing, out / 'missing_value_report.csv', index=False)
    high_missing = missing.loc[missing['over_90_percent']]
    print('Columns >90% null:', high_missing['column'].tolist())
    save_table(high_missing, out / 'high_missing_columns.csv', index=False)

    # 5. All nine numeric fields (where present); coerce invalid strings for EDA only.
    available = [col for col in NUMERIC_FIELDS if col in df.columns]
    unavailable = [col for col in NUMERIC_FIELDS if col not in df.columns]
    print('Numeric fields available:', available)
    print('Numeric fields absent:', unavailable)
    numeric = df[available].apply(pd.to_numeric, errors='coerce')
    if available:
        summary = numeric.describe(percentiles=PERCENTILES).T
        summary['median'] = numeric.median()
        summary['coerced_or_missing_count'] = numeric.isna().sum()
        print('Numeric summary:\n', summary.to_string())
        save_table(summary, out / 'numeric_distribution_summary.csv')

        # 6. Histogram and boxplot for each available nonempty field.
        for col in available:
            values = numeric[col].dropna()
            if values.empty:
                print(f'Skipping plots for {col}: no numeric values.')
                continue
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.hist(values, bins=50)
            ax.set(title=f'{kind.title()}: {col} histogram', xlabel=col, ylabel='Frequency')
            fig.tight_layout()
            fig.savefig(plots / f'{col}_histogram.png', dpi=140)
            plt.close(fig)

            fig, ax = plt.subplots(figsize=(8, 3))
            ax.boxplot(values, vert=False)
            ax.set(title=f'{kind.title()}: {col} boxplot', xlabel=col)
            fig.tight_layout()
            fig.savefig(plots / f'{col}_boxplot.png', dpi=140)
            plt.close(fig)

        # 7. Extreme-value screening: strictly outside 1st/99th percentiles.
        outlier_rows = []
        for col in available:
            values = numeric[col].dropna()
            if values.empty:
                outlier_rows.append({'field': col, 'p01': float('nan'),
                                     'p99': float('nan'), 'extreme_count': 0,
                                     'non_null_count': 0, 'extreme_percent': float('nan')})
                continue
            lo, hi = values.quantile([0.01, 0.99])
            n_extreme = int(((values < lo) | (values > hi)).sum())
            outlier_rows.append({'field': col, 'p01': lo, 'p99': hi,
                                 'extreme_count': n_extreme,
                                 'non_null_count': len(values),
                                 'extreme_percent': 100 * n_extreme / len(values)})
        outliers = pd.DataFrame(outlier_rows)
        print('Potential extreme values (screen only):\n', outliers.to_string(index=False))
        save_table(outliers, out / 'potential_outliers.csv', index=False)

    # 8. Suggested EDA questions: price and market comparisons are SOLD-specific.
    insights = [
    f'Dataset: {kind}',
    f'Total Residential rows: {len(df):,}',
    'PropertyType: Residential (filtered in Week 1)'
]
    if kind == 'sold':
        if 'ClosePrice' in df.columns:
            prices = pd.to_numeric(df['ClosePrice'], errors='coerce')
            insights.append(f'Mean close price (non-null): {prices.mean():,.2f}')
            insights.append(f'Median close price (non-null): {prices.median():,.2f}')
        if 'DaysOnMarket' in numeric.columns:
            insights.append('DaysOnMarket summary:\n' + numeric['DaysOnMarket'].describe().to_string())
        if {'ClosePrice', 'ListPrice'}.issubset(df.columns):
            cp = pd.to_numeric(df['ClosePrice'], errors='coerce')
            lp = pd.to_numeric(df['ListPrice'], errors='coerce')
            valid = cp.notna() & lp.notna() & (cp > 0) & (lp > 0)
            denominator = int(valid.sum())
            if denominator:
                insights += [
                    f'Valid sold/list price pairs: {denominator:,}',
                    f'Sold above list: {100 * (valid & (cp > lp)).sum() / denominator:.2f}%',
                    f'Sold below list: {100 * (valid & (cp < lp)).sum() / denominator:.2f}%',
                    f'Sold at list: {100 * (valid & (cp == lp)).sum() / denominator:.2f}%',
                ]
        if {'ListingContractDate', 'CloseDate'}.issubset(df.columns):
            listed = pd.to_datetime(df['ListingContractDate'], errors='coerce')
            closed = pd.to_datetime(df['CloseDate'], errors='coerce')
            comparable = listed.notna() & closed.notna()
            anomalies = comparable & (closed < listed)
            insights.append(f'Close before listing: {int(anomalies.sum()):,} / {int(comparable.sum()):,} comparable dates')
        if {'CountyOrParish', 'ClosePrice'}.issubset(df.columns):
            temp = pd.DataFrame({'county': df['CountyOrParish'],
                                 'price': pd.to_numeric(df['ClosePrice'], errors='coerce')})
            temp = temp.loc[temp['price'] > 0]
            county = (temp.groupby('county', dropna=True)['price']
                      .agg(['median', 'count']).sort_values('median', ascending=False))
            save_table(county, out / 'county_median_close_prices.csv')
            insights.append('Top 10 counties by median close price (sample sizes included):\n' + county.head(10).to_string())
    else:
        if 'ListPrice' in numeric.columns:
            insights.append(f'Mean list price: {numeric["ListPrice"].mean():,.2f}')
            insights.append(f'Median list price: {numeric["ListPrice"].median():,.2f}')
        if 'DaysOnMarket' in numeric.columns:
            insights.append('DaysOnMarket summary:\n' + numeric['DaysOnMarket'].describe().to_string())

    insights_text = '\n'.join(insights) + '\n'
    print('EDA questions and findings:\n', insights_text)
    (out / 'eda_findings.txt').write_text(insights_text, encoding='utf-8')


def main():
    for kind, path in INPUTS.items():
        analyze_dataset(kind, path)
    print('\nFinished Weeks 2-3 Part 1. Review outputs/private/ locally.')


if __name__ == '__main__':
    main()
