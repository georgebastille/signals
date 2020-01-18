import pandas as pd
import datetime
from collections import defaultdict
from supertrend.Indicators.Super_Trend import ST


ohlc_dict = {'Open':'first', 'High':'max', 'Low':'min', 'Close': 'last'}


loaded = {}

def load_ticker(ticker, sample_mins=None):
    if (ticker, sample_mins) in loaded:
        return loaded[(ticker, sample_mins)]
    
    filename = f"./csv/{ticker}.csv"
    #print(f"Loading {filename}")
    df = pd.read_csv(filename, 
                       names=['Datetime', 'Open', 'High', 'Low', 'Close'], 
                       index_col='Datetime', 
                       parse_dates=True, 
                       infer_datetime_format=True)
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

supertrends = {}

def get_supertrend(ticker, multiplier, length, sample_mins=None):
    if (ticker, sample_mins, multiplier, length) in supertrends:
        return supertrends[(ticker, sample_mins, multiplier, length)]
    df = load_ticker(ticker, sample_mins)
    dfs = ST(df, multiplier, length)[["Open","High","Low","Close","SuperTrend","SuperTrendType"]]
    supertrends[(ticker, sample_mins, multiplier, length)] = dfs
    return dfs           
    
class Signal:
    def __init__(self, ticker, datetime_str, entry_price, stop_loss, take_profit):
        # Signal time needs to be in the format '2020-02-01 19:34'
        self.datetime_str = datetime_str
        self.signal_time = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        self.entry_price = float(entry_price)
        self.stop_loss = float(stop_loss)
        self.take_profit = float(take_profit)
        self.type = "BUY" if take_profit > stop_loss else "SELL"
        self.ticker = ticker
        
    def __str__(self):
        return f"{self.ticker}: {self.datetime_str}: Entry: {self.entry_price}, SL: {self.stop_loss}, TP: {self.take_profit}"
        
    def set_stop_loss_pips(self, new_stop_loss):
        stop_loss_pair_val = new_stop_loss / pip_factor(self.ticker)
        if self.type == "BUY":
            self.stop_loss = self.entry_price - stop_loss_pair_val
        if self.type == "SELL":
            self.stop_loss = self.entry_price + stop_loss_pair_val

        
    def set_take_profit_pips(self, new_take_profit):
        take_profit_pair_val = new_take_profit / pip_factor(self.ticker)
        if self.type == "BUY":
            self.take_profit = self.entry_price + take_profit_pair_val
        if self.type == "SELL":
            self.take_profit = self.entry_price - take_profit_pair_val
        
        
def pip_factor(ticker):
    factor = 10000
    if "JPY" in ticker:
        factor = 100
        
    if "XAU" in ticker:
        factor = 10
    return factor


def load_beta_trades(filename):
    signals = defaultdict(list)
    with open(filename, 'r') as f:
        next(f) # Skip header row
        for signal in f:
            tokens = signal.split(",")
            datetime = tokens[0].strip()
            ticker = tokens[1].strip()
            signal_type = tokens[2].strip()
            entry = tokens[3].strip()
            tp1 = tokens[4].strip()
            tp2 = tokens[6].strip()
            tp3 = tokens[8].strip()
            sl = tokens[10].strip()
            signals["TP1"].append(Signal(ticker, datetime, entry, sl, tp1))
            signals["TP2"].append(Signal(ticker, datetime, entry, sl, tp2))
            signals["TP3"].append(Signal(ticker, datetime, entry, sl, tp3))
    return signals
