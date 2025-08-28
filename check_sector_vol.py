import pandas as pd
import numpy as np

# Load one of the cached data files to check sector_vol values
df = pd.read_parquet('data_cache/RELIANCE.NS_2018-01-01_2025-08-25.parquet')

print('Sector volatility statistics:')
print(f'Min: {df["sector_vol"].min():.2f}%')
print(f'Max: {df["sector_vol"].max():.2f}%')
print(f'Mean: {df["sector_vol"].mean():.2f}%')
print(f'Median: {df["sector_vol"].median():.2f}%')
print(f'95th percentile: {df["sector_vol"].quantile(0.95):.2f}%')
print(f'Values below 5%: {(df["sector_vol"] < 5).sum()} out of {len(df)} days')
print(f'Values below 15%: {(df["sector_vol"] < 15).sum()} out of {len(df)} days')

# Show some sample values
print('\nSample sector_vol values:')
print(df["sector_vol"].head(10))
