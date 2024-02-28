from constants import *
from utils import format_price
from public_functions import get_candles_recent
from private_functions import is_open_positions
from cointegration import calculate_zcore
from bot import BotAgent
import pandas as pd
import json
from pprint import pprint

# Open positions
def open_positions(client):
  """
  Manage finding triggers for trade entry
  Store trades for managing later on exit funtion"""

  # Load cointegrated pairs
  df = pd.read_csv("cointegrated_pairs.csv")

  markets = client.public.get_markets().data["markets"]

    # Opening json file
  try:
    with open("bot_agents.json") as f:
      open_trades_dict = json.load(f)

    bot_agents = [position for position in open_trades_dict if position["pair_status"] == "LIVE"]
    pprint(bot_agents)
  except Exception as e:
    bot_agents = []

  for index, row in df.iterrows():
    # Get market details
    market_1 = row["market1"]
    market_2 = row["market2"]
    hedge_ratio = row["hedge_ratio"]
    half_life = row["half_life"]

    series1 = get_candles_recent(client, market_1)
    series2 = get_candles_recent(client, market_2)
    
    # Calculate z-score
    if len(series1) > 0 and len(series1) == len(series2):
      spread = series1 - (hedge_ratio * series2)
      z_score = calculate_zcore(spread).values.tolist()[-1]
      
      # Check if z-score is within range
      if abs(z_score) >= Z_SCORE_THRESHOLD:
        is_base_open = is_open_positions(client, market_1)
        is_quote_open = is_open_positions(client, market_2)

        if not is_base_open and not is_quote_open:
          base_side = "BUY" if z_score < 0 else "SELL"
          quote_side = "BUY" if z_score > 0 else "SELL"

        base_price = series1[-1]
        quote_price = series2[-1]
        accept_base_price = float(base_price) *1.01 if z_score < 0 else float(base_price) * 0.99
        accept_quote_price = float(quote_price) *1.01 if z_score > 0 else float(quote_price) * 0.99
        fail_safe_base_price = float(base_price) * 0.05 if z_score < 0 else float(base_price) * 1.7
        base_tick_size = markets[market_1]["tickSize"]
        quote_tick_size = markets[market_2]["tickSize"]

        # Format prices
        accept_base_price = format_price(accept_base_price, base_tick_size)
        accept_quote_price = format_price(accept_quote_price, quote_tick_size)
        accept_failsafe_base_price = format_price(fail_safe_base_price, base_tick_size)

        # Get size
        base_quantity = 1 / base_price * USD_PER_TRADE
        quote_quantity = 1 / quote_price * USD_PER_TRADE
        base_step_size = markets[market_1]["stepSize"]  
        quote_step_size = markets[market_2]["stepSize"]

        # Format quantity
        base_quantity = format_price(base_quantity, base_step_size)
        quote_quantity = format_price(quote_quantity, quote_step_size)

        # Ensure size is within limits
        base_min_order_size = markets[market_1]["minOrderSize"]
        quote_min_order_size = markets[market_2]["minOrderSize"]
        check_base = float(base_quantity) > float(base_min_order_size)
        check_quote = float(quote_quantity) > float(quote_min_order_size)

        if check_base and check_quote:
          # Check account balance
          account = client.private.get_account().data
          free_collateral = float(account["account"]["freeCollateral"])  
          print(f"Balance: {free_collateral} and minimum at {USD_MIN_COLLATERAL}")

          if free_collateral < USD_MIN_COLLATERAL:
            break

          # Create bot agent
          bot_agent = BotAgent(client, market_1=market_1, market_2=market_2, base_side=base_side, base_size=base_quantity, base_price=accept_base_price, quote_side=quote_side, quote_size=quote_quantity, quote_price=accept_quote_price, accept_failsafe_base_price=accept_failsafe_base_price, z_score=z_score, half_life=half_life, hedge_ratio=hedge_ratio)

          # Open trades
          bot_open_dict = bot_agent.open_trades()

          # handle sucessful trades
          if bot_open_dict["pair_status"] == "LIVE":
            bot_agents.append(bot_open_dict)
            del bot_agent
            print("Trade status: LIVE\n ----")
          else:
            print(f"Trade status: {bot_open_dict['comments']}\n ----")

  # Save bot agents
  print(f"Saving bot agents: {len(bot_agents)} pairs live")
  if len(bot_agents) > 0:
    with open("bot_agents.json", "w") as f:
      json.dump(bot_agents, f, indent=4)
    