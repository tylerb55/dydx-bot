from constants import CLOSE_AT_Z_SCORE_CROSS
from utils import format_price
from public_functions import get_candles_recent
from cointegration import calculate_zcore
from private_functions import place_market_order
import json
from pprint import pprint
import time

# Manage trade exits
def manage_trade_exits(client):
  """
  Manage exiting open positions ofBased upon criteria set in constants
  """

  save_output = []

  # Opening json file
  try:
    with open("bot_agents.json") as f:
      open_trades_dict = json.load(f)
  except Exception as e:
    print(f"Error opening bot_agents.json: {e}")
    return "Error"
  
  # Exit if no positions in file
  if len(open_trades_dict) == 0:
    print("No open positions found")
    return "No open positions found"
  
  # Get all open positions
  exchange_positions = client.private.get_positions(status="OPEN").data["positions"]
  all_exc_positions = [pos["market"] for pos in exchange_positions]

  # Protect API from request limit
  time.sleep(1)

  # check all saved positions match order record
  # Exit trade acoring to trade exit criteria
  for position in open_trades_dict:
    is_close = False

    # Extract position matching information from file - market 1
    position_market_m1 = position["market_1"]
    position_size_m1 = position["order_m1_size"]
    position_side_m1 = position["order_m1_side"]

    # Extract position matching information from file - market 2
    position_market_m2 = position["market_2"]
    position_size_m2 = position["order_m2_size"]
    position_side_m2 = position["order_m2_side"]

    # Protect API from request limit
    time.sleep(1)

    # Get order info m1 
    order_m1 = client.private.get_order_by_id(position["order_m1_id"]).data
    order_market_m1 = order_m1["order"]["market"]
    order_size_m1 = order_m1["order"]["size"]
    order_side_m1 = order_m1["order"]["side"]

    # Protect API from request limit
    time.sleep(1)

    # Get order info m2
    order_m2 = client.private.get_order_by_id(position["order_m2_id"]).data
    order_market_m2 = order_m2["order"]["market"]
    order_size_m2 = order_m2["order"]["size"]
    order_side_m2 = order_m2["order"]["side"]

    # Perform checks
    check_m1 = position_market_m1 == order_market_m1 and position_size_m1 == order_size_m1 and position_side_m1 == order_side_m1
    check_m2 = position_market_m2 == order_market_m2 and position_size_m2 == order_size_m2 and position_side_m2 == order_side_m2
    check_live = position_market_m1 in all_exc_positions and position_market_m2 in all_exc_positions

    # Exit trade if checks fail
    if not check_m1 or not check_m2 or not check_live:
      print(f"Trade {position_market_m1} vs {position_market_m2} does not match order records")
      continue

    # Get prices
    series1 = get_candles_recent(client, position_market_m1)
    time.sleep(1)
    series2 = get_candles_recent(client, position_market_m2)
    time.sleep(1)

    # Get markets for reference of tick size
    market = client.public.get_markets().data["markets"]

    time.sleep(1)

    # Trigger close based on z-score
    if CLOSE_AT_Z_SCORE_CROSS:
      print(series1[-1], series2[-1])
      z_score_traded = position["z_score"]
      if len(series1) > 0 and len(series1) == len(series2):
        spread = series1 - (position["hedge_ratio"] * series2)
        z_score = calculate_zcore(spread).values.tolist()[-1]
      
      z_score_level_check = abs(z_score) >= abs(z_score_traded)
      z_score_cross_check = (z_score > 0 and z_score_traded < 0) or (z_score < 0 and z_score_traded > 0)

      if z_score_level_check and z_score_cross_check:
        is_close = True

    # Any other exit criteria can be added here
    # Trigger is_close = True if exit criteria is met
        
    # Close trade if is_close is True
    if is_close:
      print(f"Trade {position_market_m1} vs {position_market_m2} is being closed")
      # Close position
      side_m1 = "SELL" if position_side_m1 == "BUY" else "BUY"
      side_m2 = "SELL" if position_side_m2 == "BUY" else "BUY"
      price_m1 = series1[-1]
      price_m2 = series2[-1]
      accept_price_m1 = price_m1 * 1.05 if side_m1 == "BUY" else price_m1 * 0.95
      accept_price_m2 = price_m2 * 1.05 if side_m2 == "BUY" else price_m2 * 0.95
      accept_price_m1 = format_price(accept_price_m1, market[position_market_m1]["tickSize"])
      accept_price_m2 = format_price(accept_price_m2, market[position_market_m2]["tickSize"])

      # Close position
      try:
        place_market_order(client, position_market_m1, side_m1, position_size_m1, accept_price_m1, True)
        time.sleep(1)
        place_market_order(client, position_market_m2, side_m2, position_size_m2, accept_price_m2, True)
      except Exception as e:
          print(f"Error closing trade {position_market_m1} vs {position_market_m2}: {e}")
          save_output.append(position)
          
    else:
      save_output.append(position)

  # Save open trades
  print(f"Saving open trades: {save_output}. Length: {len(save_output)}")
  with open("bot_agents.json", "w") as f:
    json.dump(save_output, f, indent=2)
