from decouple import config
from dydx3 import Client
from web3 import Web3
from dash import Dash, dcc, html
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from tqdm import tqdm
import requests
import time
from pprint import pprint
from datetime import datetime
from utils import get_ISO_times
from constants import (
  API_HOST,
  ETHEREUM_ADDRESS,
  DYDX_API_KEY,
  DYDX_API_SECRET,
  DYDX_API_PASSPHRASE,
  STARK_PRIVATE_KEY,
  HTTP_PROVIDER,
  TELEGRAM_BOT_TOKEN,
  TELEGRAM_CHAT_ID,
  MODE,
  RESOLUTION
)

def connect_to_dydx():
  client = Client(
      host=API_HOST,
      api_key_credentials={
          "key":DYDX_API_KEY,
          "secret":DYDX_API_SECRET,
          "passphrase":DYDX_API_PASSPHRASE
      },
      stark_private_key=STARK_PRIVATE_KEY,
      eth_private_key=config('ETH_PRIVATE_KEY_TESTNET' if MODE == 'DEVELOPMENT' else 'ETH_PRIVATE_KEY_MAINNET'),
      default_ethereum_address=ETHEREUM_ADDRESS,
      web3=Web3(Web3.HTTPProvider(HTTP_PROVIDER))
  )

  account = client.private.get_account()
  account_id = account.data["account"]["id"]
  quote_balance = account.data["account"]["quoteBalance"]
  print("Connected Suceessfully to dydx")
  print(f"Account ID: {account_id}")
  print(f"Quote Balance: {quote_balance}")

  return client

# Get recent candles
def get_candles_recent(client, market):
  # Protect API from request limit
  time.sleep(1)

  # Get data
  candles = client.public.get_candles(
    market=market,
    resolution=RESOLUTION
  ).data["candles"]

  close_prices = [candle["close"] for candle in candles]
  close_prices.reverse()
  prices_result = np.array(close_prices).astype(float)
  return prices_result

def get_candles_historical(client, market):
  ISO_TIMES = get_ISO_times()

  all_candles = []

  for timeframe in ISO_TIMES.keys():
    tf_obj = ISO_TIMES[timeframe]
    from_iso = tf_obj["from_iso"]
    to_iso = tf_obj["to_iso"]

    # Protect API from request limit
    time.sleep(1)

    candles = client.public.get_candles(
      market=market,
      resolution=RESOLUTION,
      from_iso=from_iso,
      to_iso=to_iso
    ).data["candles"]

    #pprint(candles)

    # Structure data
    for candle in candles:
      all_candles.append({
        "datetime": candle["startedAt"],
        "open": candle["open"],
        "high": candle["high"],
        "low": candle["low"],
        "close": candle["close"],
        "volume": candle["trades"],
        market: candle["close"],
        "plotly_start": datetime.fromisoformat(candle["startedAt"].split(".")[0]),
      })

  all_candles.reverse()
  return all_candles

def construct_market_prices(client):
  # Declare variables
  tradeable_markets = []
  markets = client.public.get_markets().data["markets"]

  # Find tradeable pairs
  for market in markets.keys():
    if markets[market]["status"] == "ONLINE" and markets[market]["type"] == "PERPETUAL":
      tradeable_markets.append(market)

  df = pd.DataFrame()
  # Set initial DataFrame
  for market in tqdm(tradeable_markets):
    close_prices = get_candles_historical(client, market)
    df_new = pd.DataFrame(close_prices)[["datetime", market]]
    df_new.set_index("datetime", inplace=True)
    df = pd.concat([df, df_new], axis=1)
    del df_new

  df = df.dropna()
  print(df)
  return df

def make_candles_chart(candles):
  fig = go.Figure(data=[go.Candlestick(x=[candle["plotly_start"] for candle in candles],
                                       open=[candle["open"] for candle in candles],
                                       high=[candle["high"] for candle in candles],
                                       low=[candle["low"] for candle in candles],
                                       close=[candle["close"] for candle in candles])])
  return fig

def plot_figures(fig):
  app = Dash()
  app.layout = html.Div([
      dcc.Graph(figure=fig)
  ])
  app.run_server(debug=True, use_reloader=True)

def telegram_bot_sendtext(bot_message):
  bot_token = TELEGRAM_BOT_TOKEN
  bot_chatID = TELEGRAM_CHAT_ID
  send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
  response = requests.get(send_text)
  return response.json()