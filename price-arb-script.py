import pandas as pd
from datetime import datetime

# The print commands below are simply there to help with debugging. Remove if not desired

# Prompt the user for the ticker
ticker = input("Enter the ticker: ")

# Read the first input file
tradesdata = pd.read_csv(f'{ticker}-trades.csv')
tradesdata = tradesdata[['date_rounded', 'price', 'net_skew', 'skewscale']]
tradesdata['date_rounded'] = tradesdata['date_rounded'].astype(str)  # Convert to string
tradesdata['net_skew'] = pd.to_numeric(tradesdata['net_skew'], errors='coerce')  # Convert to numeric
tradesdata['price'] = pd.to_numeric(tradesdata['price'], errors='coerce')  # Convert to numeric

# Rename the 'price' column to 'trade_price
tradesdata.rename(columns={'price': 'trade_price'}, inplace=True)

# Remove commas from the skewscale column
tradesdata['skewscale'] = tradesdata['skewscale'].astype(str).str.replace(',', '')
tradesdata['skewscale'] = pd.to_numeric(tradesdata['skewscale'], errors='coerce')  # Convert to numeric

print("Trades Data:")
print(tradesdata.head())

# Read the second input file
pythdata = pd.read_csv(f'{ticker}-pyth-prices.csv')
print("\nPyth Data (before filtering):")
print(pythdata.head())
print(f"Unique values in 't' column: {pythdata['t'].unique()}")

# Only include price data for the timestamps that appear in the tradesdata file (i.e. discard Pyth price data for which there are no trades on Synthetix)
pythdata = pythdata[pythdata['t'].isin(tradesdata['date_rounded'])]
pythdata = pythdata[['t','h', 'l']]
pythdata.rename(columns={'t': 'Pyth-time', 'h': 'Pyth-h', 'l': 'Pyth-l'}, inplace=True)
print("\nPyth Data (after filtering):")
print(pythdata.head())

# Read the third input file
binancedata = pd.read_csv(f'{ticker}-binance-prices.csv')
print("\nBinance Data (before filtering):")
print(binancedata.head())
print(f"Unique values in 'open_time_standardized' column: {binancedata['open_time_standardized'].unique()}")

# Only include price data for the timestamps that appear in the tradesdata file (i.e. discard Binance price data for which there are no trades on Synthetix)
binancedata = binancedata[binancedata['open_time_standardized'].isin(tradesdata['date_rounded'])]
binancedata = binancedata[['open_time_standardized','high', 'low']]
binancedata.rename(columns={'open_time_standardized': 'Binance-time', 'high': 'Binance-h', 'low': 'Binance-l'}, inplace=True)
print("\nBinance Data (after filtering):")
print(binancedata.head())

# Merge the dataframes based on the timestamp columns
merged_data = pd.merge(tradesdata, pythdata, left_on='date_rounded', right_on='Pyth-time', how='left')
merged_data = pd.merge(merged_data, binancedata, left_on='date_rounded', right_on='Binance-time', how='left')

print("\nMerged Data:")
print(merged_data.head())

# Perform calculations on the merged dataframe

# Calculate the Synthetix price (low and high)
merged_data['Syn-l'] = merged_data['Pyth-l'] * (1 + (merged_data['net_skew'] / merged_data['skewscale']))
merged_data['Syn-h'] = merged_data['Pyth-h'] * (1 + (merged_data['net_skew'] / merged_data['skewscale']))

# Calculate the difference between the Synthetix price and the Binance price: Synthetix high - Binance low (in which case you short on Synthetix), or Synthetix low - Binance high (in which case you short on Binance). Pick the difference that is largest in absolute
merged_data['deviation_sh-bl'] = merged_data['Syn-h'] - merged_data['Binance-l']
merged_data['deviation_sl-bh'] = merged_data['Syn-l'] - merged_data['Binance-h']
merged_data['deviation_max'] = merged_data[['deviation_sh-bl', 'deviation_sl-bh']].abs().max(axis=1)

# Calculate the deviation in % and use that to calculate the profit opportunity in $, based on theh formula Profit Opp = Deviation (%) * Price ($) * Net Skew * 1/2
merged_data['deviation_max_pct'] = merged_data['deviation_max'] / merged_data['trade_price']
merged_data['profit_opp_dollars'] = merged_data['deviation_max_pct'] * merged_data['trade_price'] * merged_data['net_skew'].abs() * 0.5

# Prepare the outputs

# Get the current timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Save the merged data to a new CSV file with "profitopp" in the file name and include a timestamp
output_file = f'{ticker}_profitopp_{timestamp}.csv'
merged_data.to_csv(output_file, index=False, float_format='%.18f')
print(f"\nOutput file saved as: {output_file}")

# Sort the merged data by 'profit_opp_dollars' column in descending order
merged_data_sorted = merged_data.sort_values('profit_opp_dollars', ascending=False)

# Select the top 20 rows and the specified columns
merged_data_top20 = merged_data_sorted.head(20)[['date_rounded', 'trade_price', 'net_skew', 'deviation_max_pct', 'profit_opp_dollars']]

# Save the top 20 rows to a new CSV file with "profitopp_ranked-trunc" in the file name and include a timestamp
output_file_top20 = f'{ticker}_profitopp_ranked-trunc_{timestamp}.csv'
merged_data_top20.to_csv(output_file_top20, index=False, float_format='%.18f')
print(f"\nTop 20 rows saved as: {output_file_top20}")