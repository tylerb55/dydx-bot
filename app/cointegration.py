import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint
import statsmodels.api as sm
from constants import MAX_HALF_LIFE, WINDOW

def calculate_half_life(spread):
  df_spread = pd.DataFrame(spread, columns=["spread"])
  spread_lag = df_spread.spread.shift(1)
  spread_lag.iloc[0] = spread_lag.iloc[1]
  spread_ret = df_spread.spread - spread_lag
  spread_ret.iloc[0] = spread_ret.iloc[1]
  spread_lag2 = sm.add_constant(spread_lag)
  model = sm.OLS(spread_ret, spread_lag2)
  res = model.fit()
  halflife = int(round(-np.log(2) / res.params[1], 0))
  return halflife

def calculate_zcore(spread):
  spread_series = pd.Series(spread)
  mean = spread_series.rolling(center=False, window=WINDOW).mean()
  std = spread_series.rolling(center=False, window=WINDOW).std()
  x = spread_series.rolling(center=False, window=1).mean()
  zscore = (x - mean) / std
  return zscore

# can add intercept if performance is not good
def calculate_cointegration(series1, series2):
  series1 = np.array(series1).astype(float)
  series2 = np.array(series2).astype(float)
  conint_flag = False
  coint_res = coint(series1, series2)
  coint_t = coint_res[0]
  p_value = coint_res[1]  
  critical_value = coint_res[2][1]
  model = sm.OLS(series1, series2).fit()
  hedge_ratio = model.params[0]
  spread = series1 - (hedge_ratio * series2)
  half_life = calculate_half_life(spread)
  t_check = coint_t < critical_value # can swap the < to > if you want to check for the null hypothesis
  coint_flag = t_check and p_value < 0.05
  return coint_flag, hedge_ratio, half_life 

def store_cointegration_results(df_market_prices):
  # Declare variables
  cointegrated_pairs = []
  markets = df_market_prices.columns.tolist()
  # Find cointegrated pairs
  for index, market1 in enumerate(markets[:-1]):
    series1 = df_market_prices[market1].values.astype(float).tolist()
  
    for market2 in markets[index+1:]:
      series2 = df_market_prices[market2].values.astype(float).tolist()
      cointegrated, hedge_ratio, half_life = calculate_cointegration(series1, series2)
      if cointegrated and half_life > 0 and half_life <= MAX_HALF_LIFE:
        cointegrated_pairs.append({
          "market1": market1,
          "market2": market2,
          "hedge_ratio": hedge_ratio,
          "half_life": half_life
        })

      df_cointegrated_pairs = pd.DataFrame(cointegrated_pairs)
      df_cointegrated_pairs.to_csv("cointegrated_pairs.csv", index=False)
      del df_cointegrated_pairs

  print("Cointegrated pairs saved")
  return "saved" if len(cointegrated_pairs) > 0 else "no cointegrated pairs found"

      
