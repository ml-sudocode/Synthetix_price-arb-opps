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
### add: calc the average of Pyth price between h and l 
pythdata.rename(columns={'t': 'Pyth-time', 'h': 'Pyth-h', 'l': 'Pyth-l'}, inplace=True)
print("\nPyth Data (after filtering):")
print(pythdata.head())

# Merge the dataframes based on the timestamp columns
merged_data = pd.merge(tradesdata, pythdata, left_on='date_rounded', right_on='Pyth-time', how='left')

print("\nMerged Data:")
print(merged_data.head())

# Calculate the profit opportunity in $, based on the formula Profit Opp = Deviation (%) * (Price ($) * Net Skew) * 1/2; if we assume Pyth and Binance price are the same, then the formula simplifies to Profit Opp = Skew/SkewScale (%) * (Price ($) * Net Skew) * 1/2

## Note: The Price ($) chosen should be price on the CEX (or, the oracle price as a close proxy), but for simplicity here we use the actual trade price; the difference should not be significant for calculations meant only for approximation. 

merged_data['abs_skew_skewscale'] = (merged_data['net_skew'] / merged_data['skewscale']).abs()
merged_data['profit_opp_dollars'] = merged_data['abs_skew_skewscale'] * merged_data['trade_price'] * merged_data['net_skew'].abs() * 0.5

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
merged_data_top20 = merged_data_sorted.head(20)[['date_rounded', 'trade_price', 'net_skew', 'abs_skew_skewscale', 'profit_opp_dollars']]

# Save the top 20 rows to a new CSV file with "profitopp_ranked-trunc" in the file name and include a timestamp
output_file_top20 = f'{ticker}_profitopp_ranked-trunc_{timestamp}.csv'
merged_data_top20.to_csv(output_file_top20, index=False, float_format='%.18f')
print(f"\nTop 20 rows saved as: {output_file_top20}")