from datetime import datetime, timedelta


def format_price(price, tick_size):
  price_string = f"{price}"
  tick_size_string = f"{tick_size}"

  if "." in tick_size_string:
    tick_decimals = len(tick_size_string.split(".")[1])
    price_string = f"{price:.{tick_decimals}f}"
    return price_string
  else:
    return f"{int(price)}"
  
def format_time(timestamp):
  return timestamp.replace(microsecond=0).isoformat()

def get_ISO_times():
  # Get timestamps (roughly 16 days of hourly data)
  date_start_0 = datetime.now() 
  date_start_1 = date_start_0 - timedelta(hours=100)
  date_start_2 = date_start_1 - timedelta(hours=100)
  date_start_3 = date_start_2 - timedelta(hours=100)
  date_start_4 = date_start_3 - timedelta(hours=100)
  
  # Format the datetimes
  times_dict = {
    "range_1": {
      "from_iso": format_time(date_start_1),
      "to_iso": format_time(date_start_0),
      "from_datetime": date_start_1,
      "to_datetime": date_start_0
    },
    "range_2": {
      "from_iso": format_time(date_start_2),
      "to_iso": format_time(date_start_1),
      "from_datetime": date_start_2,
      "to_datetime": date_start_1
    },
    "range_3": {
      "from_iso": format_time(date_start_3),
      "to_iso": format_time(date_start_2),
      "from_datetime": date_start_3,
      "to_datetime": date_start_2
    },
    "range_4": {
      "from_iso": format_time(date_start_4),
      "to_iso": format_time(date_start_3),
      "from_datetime": date_start_4,
      "to_datetime": date_start_3
    }
  }
  return times_dict
