from utils import format_price
import time
from datetime import datetime, timedelta

# Get existing open positions
def is_open_positions(client,market):
  # Protect API from request limit  
  time.sleep(1)

  # Get open positions
  open_positions = client.private.get_positions(market=market,status="OPEN").data["positions"]

  # Determine if there are open positions
  if len(open_positions) > 0:
    return True
  else:
    return False

def check_order_status(client, order_id):
  order = client.private.get_order_by_id(order_id).data
  if order:
    if "order" in order.keys():
      return order["order"]["status"]
  return "FAILED"

def place_market_order(client, market, side, size, price, reduce_only):
  #get position id
  account_response = client.private.get_account()
  position_id = account_response.data["account"]["positionId"]

  #get expiration time
  server_time = client.public.get_time()
  expiration = datetime.fromisoformat(server_time.data["iso"].replace("Z","")) + timedelta(seconds=70)

  placed_order = client.private.create_order(
    position_id=position_id, # required for creating the order signature
    market=market,
    side=side,
    order_type="MARKET",
    post_only=False,
    size=size,
    price=price,
    limit_fee='0.015',
    expiration_epoch_seconds=expiration.timestamp(),
    time_in_force="FOK",
    reduce_only=reduce_only
  )

  return placed_order.data

def close_all_positions(client):
  # Close all open positions
  client.private.cancel_all_orders()

  # Protect API from request limit
  time.sleep(1)

  # Get markets for reference of tick size
  markets = client.public.get_markets().data["markets"]

  # Protect API from request limit
  time.sleep(1)

  # Get all open positions
  open_positions = client.private.get_positions(status="OPEN").data["positions"]

  # Handle open positions
  close_orders = []
  if len(open_positions) > 0:
    for position in open_positions:
      market = position["market"]

      side = "SELL" if position["side"] == "LONG" else "BUY"

      price = float(position["entryPrice"])
      accept_price = price * 1.7 if side == "BUY" else price * 0.3
      tick_size = markets[market]["tickSize"]
      accept_price = format_price(accept_price, tick_size)

      order = place_market_order(client, market, side, position["sumOpen"], accept_price, True)

      close_orders.append(order)

      # Protect API from request limit
      time.sleep(1)

    return close_orders