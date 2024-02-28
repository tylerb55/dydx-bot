from private_functions import place_market_order, check_order_status
from public_functions import telegram_bot_sendtext
from datetime import datetime, timedelta
import time
from pprint import pprint

# Class: Agent for mananging opening and closing trades
class BotAgent:

  """
  Primary function of the bot handles opening and checking the status of orders
  """

  def __init__(self, client, market_1, market_2, 
               base_side, base_size, base_price, 
               quote_side, quote_size, quote_price,
               accept_failsafe_base_price, z_score,
               half_life, hedge_ratio):
    self.client = client
    self.market_1 = market_1
    self.market_2 = market_2
    self.base_side = base_side
    self.base_size = base_size
    self.base_price = base_price
    self.quote_side = quote_side
    self.quote_size = quote_size
    self.quote_price = quote_price
    self.accept_failsafe_base_price = accept_failsafe_base_price
    self.z_score = z_score
    self.half_life = half_life
    self.hedge_ratio = hedge_ratio
    
    # Initialize output variable
    # Pair status options: FAILED, LIVE, CLOSE, ERROR
    self.order_dict = {
      "market_1": market_1,
      "market_2": market_2,
      "hedge_ratio": hedge_ratio,
      "z_score": z_score,
      "half_life": half_life,
      "order_m1_id": "",
      "order_m1_size": base_size,
      "order_m1_side": base_side,
      "order_m1_time": "",
      "order_m2_id": "",
      "order_m2_size": quote_size,
      "order_m2_side": quote_side,
      "order_m2_time": "",
      "pair_status": "",
      "comments": ""
    }

  # Check order status by id
  def check_order_status_by_id(self, order_id):

    # Allow time to process
    time.sleep(2)

    # Get order status
    order_status = check_order_status(self.client, order_id)
    print(f"Order status: {order_status}")

    if order_status == "CANCELED":
      print(f"{self.market_1} vs {self.market_2} order {order_id} was cancelled")
      self.order_dict["pair_status"] = "FAILED"
      return "FAILED"
    
    if order_status != "FAILED":
      time.sleep(15)
      order_status = check_order_status(self.client, order_id)

      if order_status == "CANCELED":
        print(f"{self.market_1} vs {self.market_2} order {order_id} was cancelled")
        self.order_dict["pair_status"] = "FAILED"
        return "FAILED"
      
      if order_status != "FILLED":
        self.client.private.cancel_order(order_id=order_id)
        self.order_dict["pair_status"] = "ERROR"
        print(f"{self.market_1} vs {self.market_2} order {order_id} was not filled")
        return "ERROR"
      
    return "LIVE"
    
  # Open trades
  def open_trades(self):

    print(f"Opening base trade for {self.market_1}")
    print(f"Side: {self.base_side}, Size: {self.base_size}, Price: {self.base_price}")

    try:
      base_order = place_market_order(self.client, self.market_1, self.base_side, self.base_size, self.base_price, False)

      # Store order id and time
      self.order_dict["order_m1_id"] = base_order["order"]["id"]
      self.order_dict["order_m1_time"] = datetime.now().isoformat()
    except Exception as e:
      self.order_dict["pair_status"] = "ERROR"
      self.order_dict["comments"] = f"Error placing {self.market_1} order: {e}"
      return self.order_dict
    
    # Ensure order is live
    order_status_m1 = self.check_order_status_by_id(self.order_dict["order_m1_id"])

    # Guard against failed order
    if order_status_m1 != "LIVE":
      self.order_dict["pair_status"] = "ERROR"
      self.order_dict["comments"] = f"{self.market_1} order failed"
      return self.order_dict
    
    print(f"Opening quote trade for {self.market_2}")
    print(f"Side: {self.quote_side}, Size: {self.quote_size}, Price: {self.quote_price}")

    try:
      quote_order = place_market_order(self.client, self.market_2, self.quote_side, self.quote_size, self.quote_price, False)

      # Store order id and time
      self.order_dict["order_m2_id"] = quote_order["order"]["id"]
      self.order_dict["order_m2_time"] = datetime.now().isoformat()
    except Exception as e:
      self.order_dict["pair_status"] = "ERROR"
      self.order_dict["comments"] = f"Error placing {self.market_2} order: {e}"
      print(f"Error placing {self.market_2} order: {e}")
      # Close order on market 1
      try:
        close_order = place_market_order(self.client, self.market_1, self.quote_side, self.base_size, self.accept_failsafe_base_price, True)

        # Ensure order is live 
        time.sleep(2)
        order_status_close = self.check_order_status_by_id(close_order["order"]["id"])
        print(order_status_close)
        if order_status_close != "LIVE":
          print("ABORTING PROGRAM")
          print("Unexpected error")
          print(order_status_close)

          # !! SEND ALERT TO TELEGRAM !!
          telegram_bot_sendtext(f"Error code 100: Failed to close {self.market_1} order: {str(order_status_close)} please check DYDX")


          exit(1)

      except Exception as e:
        self.order_dict["pair_status"] = "ERROR"
        self.order_dict["comments"] = f"Closing {self.market_1} order failed: {e}"

        print("ABORTING PROGRAM")
        print("Unexpected error")
        print(order_status_close)

        # !! SEND ALERT TO TELEGRAM !!
        telegram_bot_sendtext(f"Error code 100: Failed to close {self.market_1} order: {str(order_status_close)} please check DYDX")

        exit(1)
      return self.order_dict

    
    # Ensure order is live
    order_status_m2 = self.check_order_status_by_id(self.order_dict["order_m2_id"])

    # Guard against failed order
    if order_status_m2 != "LIVE":
      self.order_dict["pair_status"] = "ERROR"
      self.order_dict["comments"] = f"{self.market_2} order failed"
      
      # Close order on market 1
      try:
        close_order = place_market_order(self.client, self.market_1, self.quote_side, self.base_size, self.accept_failsafe_base_price, True)

        # Ensure order is live 
        time.sleep(2)
        order_status_close = self.check_order_status_by_id(close_order["order"]["id"])
        if order_status_close != "LIVE":
          print("ABORTING PROGRAM")
          print("Unexpected error")
          print(order_status_close)

          # !! SEND ALERT TO TELEGRAM !!

          exit(1)

      except Exception as e:
        self.order_dict["pair_status"] = "ERROR"
        self.order_dict["comments"] = f"Closing {self.market_1} order failed: {e}"

        print("ABORTING PROGRAM")
        print("Unexpected error")
        print(order_status_close)

        # !! SEND ALERT TO TELEGRAM !!

        exit(1)
      
    # Return success result
    else:
      self.order_dict["pair_status"] = "LIVE"
      return self.order_dict


