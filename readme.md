# Overview

This document describes how to generate a ranked list of price arb opportunities on Synthetix based on historical data.

Price arb opportunities are delta neutral opportunities where the price of a token on Synthetix differs from that on another venue, typically a centralized exchange ("CEX"). If the price on Synthetix is higher than on the CEX, a trader can short the token on Synthetix and go long on a CEX, and eventually close out the trades to pocket the difference. These opportunities are also sometimes referred to as PD Arb opportunities.

To calculate historical price arb opportunities, we need to pull its component parts for any one time period: oracle price, skew and skewscale (all three allowing us to calculate the price of a token on Synthetix); as well as the price of the token on a CEX.

![Formula diagram](/images/formula.jpeg)

Note: this estimation excludes fees paid to Synthetix and the CEX; slippage encountered on the CEX; and funding rate earned/paid on each venue (assumed to cancel out or be of nominal value due to short holding period).

# Parameters

1. Chosen market e.g. ETH

2. Time period e.g. 1-31 March 2024. Arb opportunities tend to be richer during periods of greater price volatility

# Outputs

1. File with the top 20 profit opps

2. File with all the profit opps, arranged chronologically

# Overall steps

1) Data Extraction. Pull data from 3 sources (Synthetix data, Pyth API, Binance API) as csv. Convert the files to xlsx file format. See [Data Extraction section](#-data-extraction) for more info

2) Data Preparation. Manually adjust the data files to make them ready for the next step. Adjustments include changing date formats, adding skew and renaming the files. See [Data Preparation section](#-data-preparation) for step-by-step instructions

3) Data analysis. Run this Python code, which will process the adjusted data files and output a file with a ranked list of the top 20 opportunities, and a file with all the opportunities in chronological order

# Data Extraction

(1) Oracle price data, such as for Pyth, can be accessed through the Pyth API: https://benchmarks.pyth.network/v1/. 

See here for a [sample implementation](/data-extraction/pyth-query.ipynb) of the data call.

(2) CEX price data, such as for Binance, can be accessed through the Binance API: https://fapi.binance.com. 

See here for a [sample implementation](/data-extraction/binance-query.ipynb) of the data call.

(3) Data updated when a trade is executed on Synthetix, i.e. skew, OI, price.

<!-- TO DISCUSS -->

_Note: While historical price data from CEX or Pyth tends to be continuous due to large volumes of trading, historical price and skew data on Synthetix are only updated when a trade is executed. Therefore, for the same time period, the data set for Synthetix is smaller than that of the other sources._

(4) skewScale during the chosen period. It is manually determined by a risk management procedure and usually changed infrequently (weeks or months). 

Run this Dune query to pull the skewScale over your chosen period: https://dune.com/queries/3603505.

The query looks to a table synthetix_optimism.PerpsV2MarketSettings_evt_ParameterUpdated, which contains indexed events from when parameters are updated (skewscale, maxmarketvalue, maker/taker fee, etc.). It filters those events for skewScale changes and then further filters based on the markets/times entered.

<!-- what about for v3 -->

# Data Preparation

## For the trade data from Synthetix

* Convert the date to a UNIX timestamp: add a column after the data column (column A) and insert this formula: `=(A2-DATE(1970,1,1))*86400`; apply this formula to the whole column. The format of this new column needs to be changed to Number: hit Ctrl+Shift+1 all together (it's a shortcut to format cells as Number). Name this column "date as timestamp". 
(For more info on date type conversion: https://exceljet.net/formulas/convert-excel-time-to-unix-time)

* Adjust the timestamps so that they are comparable to the data available pulled from the oracle and the CEX, which are set to 5-minute periods: add a column after the "date as timestamp" column (column B) and insert this formula: `=MROUND(B2,300)`, which rounds down the timestamp to the start of each 5-min mark; apply this formula to the whole column. Name this column "date_rounded".

* Sometimes the data extracted from Synthetix, Pyth and Binance are slightly misaligned, for example there may be a few hours more data from Synthetix compared to Pyth or Binance. To avoid errors in calculation (i.e. overestimating opportunities), we want to delete the extra data in the Synthetix trades file. 
Take the first and last timestamps from Pyth and Binance files and insert into the Trades spreadsheet. (As the Binance timestamp is in milliseconds rather than seconds, divide the timestamp by 1000). 
For each start time, choose the later time, i.e. `Start = max(Pyth-start,Binance-start)`. For each end time, choose the earlier time, i.e. `End = min(Pyth-start,Binance-start)`. 
Create a new column on the right with the formula `=IF(AND(C2>=$Start,C2<=$End),"include","DELETE")`. This will show you which rows you need to delete from the Trades file. Delete those rows now. 

* (Only) for data extract for v3, change the heading "skew" to "net_skew".

* Add a new column at the end titled "skewscale". 

Retrieve skewscale data using this Dune query mentioned in the Data Extraction section. Here's what the Dune output looks like for a few assets and time ranges.

![skewscale from Dune](/images/skewscale-dune.png)

To populate the new column, you can either eyeball it or use a series of equations to make it easier.
If you use a series of equations, here's what you can do: 
- paste the skew data from the Dune output into the Trades file. Delete "UTC" from the start and end times. Convert the format of those date cells to Date (hit Ctrl+1, then select Date). Use the timestamp formula to convert the dates into timestamps (`=([date]-DATE(1970,1,1))*86400`).
- create a new column titled skewscale and write a formula to automatically populate the whole column (e.g. where skewscale updated one time during the chosen time period, `=IF(([trade timestamp]]<=[end of first skew]]),[skewscale for first period]],[skewscale for second period]])`)

<!-- what about for v3 -->

* Save the file! 

## For the Pyth data

When you open the csv file in excel, you will be asked if you want to convert the digits with E notation into scientific notation. Click Convert.

On Pyth price sheet, the default date format is "General." For our script to process this column, the date format needs to be changed to number format. 
Select the dates in column A (titled "t"), then hit Ctrl+Shift+1 all together (it's a shortcut to format cells as Number).


## For the Binance data

When you open the csv file in excel, you will be asked if you want to convert the digits with E notation into scientific notation. Click Convert.

(1) Some assets have such low prices that they are priced in units of 1000 on Binance; we need to adjust the prices so that they are consistent with Synthetix and Pyth data (which typically do not do this).

Check the asset label column (column N). If it says something like 1000BONKUSDT or 1000PEPEUSDT, convert the high and low prices (columns C and D) to be consistent with Pyth and Trade data (i.e. divide the prices by 1000).

(2) The default date format from the API is General, and is represented as a timestamp in milliseconds. We want the timestamp in Number format, and in seconds.

First, select the dates and hit Ctrl+Shift+1 together (it's a shortcut to format cells as Number).

Then, add a column after the "open_time" column (column A) and insert this formula: `=(A2/1000)`; apply this to the whole column. Label this new column "open_time_standardized".


## Rename all 3 adjusted files

Rename the files with the ticker in the filename according to this template (case sensitive). 

(1) [TICKER]-trades.csv
(2) [TICKER]-pyth-prices.csv
(3) [TICKER]-binance-prices.csv

Note: if you selected more than one time period for each ticker, replace TICKER with TICKER-A, TICKER-B, etc. Make sure to enter TICKER-A or TICKER-B when prompted while the Python code is running. Alternatively, run the analysis with the files saved in different folders. 

# Contact

Questions? DM me on Twitter @michlai007.

Improvements to make? Fork and PR!

# Credits

Thanks to...
<!-- Insert profile links -->
* Troy for helping with all of this
* Synthquest for the skewScale query from Dune
* The masters of the universe for AI, without which this Python script would not exist bc the data format wrangling would have killed me