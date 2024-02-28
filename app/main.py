from utils import *
from private_functions import *
from public_functions import *
from entry_pairs_functions import *
from constants import CLOSE_ALL_POSITIONS, FIND_COINTEGRATED_PAIRS, PLACE_TRADES, MANAGE_EXITS
from cointegration import store_cointegration_results
from entry_pairs_functions import open_positions
from exit_pairs_functions import manage_trade_exits
import time
import datetime

if __name__ == '__main__':
    telegram_bot_sendtext("Starting dydx bot")
    # connect to dydx
    try:
        print("Connecting to dydx")
        client = connect_to_dydx()
    except Exception as e:
        print(f"Error connecting to dydx: {e}")
        telegram_bot_sendtext(f"Error connecting to dydx: {e}")
        exit(1)

    # abort all open positions and orders
    if CLOSE_ALL_POSITIONS:
        try:
            print("Closing all positions and orders")
            close_all_positions(client)
        except Exception as e:
            print(f"Error aborting all: {e}")
            telegram_bot_sendtext(f"Error aborting all positions: {e}")
            exit(1)
        print("All positions and orders aborted")

    # Find cointegrated pairs
    if FIND_COINTEGRATED_PAIRS:
        # Construct market prices
        try:
            print("Fetching market prices, please wait a few minutes...")
            df_market_prices = construct_market_prices(client)
        except Exception as e:
            print(f"Error constructing market prices: {e}")
            telegram_bot_sendtext(f"Error constructing market prices: {e}")
            exit(1)
        
        # Store Cointegrated Pairs
        try:
            print("Storing cointegrated pairs..")
            stores_result = store_cointegration_results(df_market_prices)
            if stores_result != "saved":
                print(f"Error storing cointegrated pairs: {stores_result}")
                telegram_bot_sendtext(f"Error storing cointegrated pairs: {stores_result}")
                exit(1)
        except Exception as e:
            print(f"Error saving cointegrated pairs: {e}")
            telegram_bot_sendtext(f"Error saving cointegrated pairs: {e}")
            exit(1)
    
    # Run as always on
    while True:   
        if MANAGE_EXITS:
            # Place Trades
            try:
                print("Managing exits...")
                manage_trade_exits(client)
            except Exception as e:
                print(f"Error managing exiting positions: {e}")
                telegram_bot_sendtext(f"Error managing exiting positions: {e}")
                exit(1)


        if PLACE_TRADES:
            # Place Trades
            try:
                print("Finding cointegrated pairs and placing trades...")
                open_positions(client)
            except Exception as e:
                print(f"Error trading pairs: {e}")
                telegram_bot_sendtext(f"Error trading pairs: {e}")
                exit(1)
            print("Trades placed")

   # candles = get_candles_historical(client, "BTC-USD")
   # plot_figures(make_candles_chart(candles))