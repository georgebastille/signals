#!/usr/bin/env python
# coding: utf-8
import datetime
import zipfile
import urllib.request
from pathlib import Path
import pandas as pd

ohlc_dict = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
loaded = {}

FULL_DATA_PATH = "./csv/"


def load_ticker(ticker, sample_mins=None, csv_path=FULL_DATA_PATH):
    if (ticker, sample_mins) in loaded:
        return loaded[(ticker, sample_mins)]

    filename = f"{csv_path}/{ticker}.csv"
    # print(f"Loading {filename}")
    try:
        df = pd.read_csv(
            filename,
            names=["Datetime", "Open", "High", "Low", "Close"],
            index_col="Datetime",
            parse_dates=True,
            infer_datetime_format=True,
        )
        # Fix forexit timezone
        # See last post here: https://forextester.com/forum/viewtopic.php?t=3175
        # If I adjust the signal time to be one hour forward, I get the correct time.
        # So I need to adjust the forex time to be one hour backwards
        df = df.set_index(df.index.values - pd.Timedelta(hours=1))
        df.sort_index(inplace=True)
        if sample_mins:
            df = df.resample(f"{sample_mins}Min").apply(ohlc_dict).dropna()

        loaded[(ticker, sample_mins)] = df
        return df
    except:
        return None


def pip_factor(ticker):
    factor = 10000
    if "JPY" in ticker:
        factor = 100
    if "XAU" in ticker:
        factor = 10
    return factor


# # Downloading historical forex data from forexite
# The url I got from [here](https://www.quantshare.com/sa-421-6-places-to-download-historical-intraday-forex-quotes-data-for-free). It has 1m resolution data for [lots](./forexite_pairs.txt) of symbols. Eah file contains one days data for all symbols. I need to rework the data, one file per symbol. Store in pandas and serialize. Need to handle time zones somehow...


def parse_row(row_from_file):
    # Row looks like:
    # EURUSD,20191101,000900,1.1150,1.1150,1.1150,1.1150
    tokens = row_from_file.split(",")
    assert len(tokens) == 7, f"Not enough tokens in: {row_from_file}"

    date_time_str = str(tokens[1]) + str(tokens[2])
    dt = datetime.datetime.strptime(date_time_str, "%Y%m%d%H%M%S")

    ticker = tokens[0].strip()
    opener = tokens[3].strip()
    high = tokens[4].strip()
    low = tokens[5].strip()
    close = tokens[6].strip()

    return ticker, (dt, opener, high, low, close)


if __name__ == "__main__":
    print("Downloads forex data from forexite for the last 10 years.")
    print("- Skips files already downloaded (can be run everyday)")
    print("- Converts files from one-day-per-file to one-ticker-per-file")

    date = datetime.datetime.now()
    # example forexite.com data url:
    # "https://www.forexite.com/free_forex_quotes/2011/11/011111.zip"
    url = "https://www.forexite.com/free_forex_quotes/{}/{:02d}/{:02d}{:02d}{:02d}.zip"
    filename = "./forexite/{:04d}-{:02d}-{:02d}.zip"
    new_files = []

    for x in range(1, 7 * 365):
        data_date = date - datetime.timedelta(days=x)
        year = data_date.year
        year_2 = int(str(year)[-2:])
        month = data_date.month
        day = data_date.day
        download = url.format(year, month, day, month, year_2)
        file = filename.format(year, month, day)
        file_obj = Path(file)
        if not file_obj.exists():
            print(download)
            if not Path("./forexite").is_dir():
                Path("./forexite").mkdir()
            urllib.request.urlretrieve(download, file)
            new_files.append(file_obj)

    # Converting to csv files, one ticker per file
    file_handles = {}

    print("Generating file list")
    # Only process newly downloaded files
    files = new_files
    if not new_files:
        files = Path("./forexite/").glob("*.zip")
    files = sorted(list(files))

    if not Path("./csv").is_dir():
        print("Creating output directory")
        Path("./csv").mkdir()

    print("Parsing available tickers and Opening output files")
    with zipfile.ZipFile(files[-1]) as z:
        fn = z.namelist()[0]
        print(f"Processing {fn}")
        with z.open(fn) as f:
            next(f)
            for row in f:
                clean_row = row.decode("utf-8").strip()
                ticker, ohlc = parse_row(clean_row)
                if ticker not in file_handles:
                    file_handles[ticker] = open(f"./csv/{ticker}.csv", "a")

    print("Parsing files")
    for file in files:
        with zipfile.ZipFile(file) as z:
            fn = z.namelist()[0]
            print(f"Processing {fn}")
            with z.open(fn) as f:
                next(f)
                for row in f:
                    clean_row = row.decode("utf-8").strip()
                    ticker, ohlc = parse_row(clean_row)
                    if ticker not in file_handles:
                        continue
                    file_handles[ticker].write("{}, {}, {}, {}, {}\n".format(*ohlc))

    print("Closing output files")
    for _, handle in file_handles.items():
        handle.close()
