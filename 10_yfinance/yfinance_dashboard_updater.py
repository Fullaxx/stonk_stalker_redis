#!/usr/bin/env python3
# https://redis-py.readthedocs.io/en/stable/advanced_features.html
# https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html
# https://redis-py.readthedocs.io/en/v4.3.1/examples/asyncio_examples.html
# https://aioredis.readthedocs.io/en/v1.3.0/mpsc.html
# https://medium.com/@imamramadhanns/working-with-redis-keyspace-notifications-x-python-c5c6847368a
# https://medium.com/nerd-for-tech/redis-getting-notified-when-a-key-is-expired-or-changed-ca3e1f1c7f0a
# https://tech.webinterpret.com/redis-notifications-python/
# https://redis.io/docs/manual/keyspace-notifications/

import os
import sys
import json
import redis
import signal
import datetime

import pytz
#g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

import time
usleep = lambda x: time.sleep(x/1000000.0)

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_shutdown = False
g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def yfinance_dashboard_save(symbol, key, val):
	if val is None:
		eprint(f'{key} has NULL vlaue - NOT SETTING!')
		return

	result = g_rc.set(key, val)
	if result:
		print(f'SET {key:<20} {val}', flush=True)
	else:
		eprint(f'SET {key:<20} FAILED!')

def yfinance_handle_new_stock_dailyindicators(key, symbol):
	val = g_rc.get(key)
	daily = json.loads(val)
	lyc = daily['LASTYEARCLOSE']
	key = f'DASHBOARD:DATA:LASTYEARCLOSE:{symbol}'
	yfinance_dashboard_save(symbol, key, lyc)
	sma200 = daily['SMA_200']
	key = f'DASHBOARD:DATA:SMA200:{symbol}'
	yfinance_dashboard_save(symbol, key, sma200)
	bb_lo = daily['BB_LOWER']
	bb_mid = daily['BB_MID']
	bb_hi = daily['BB_UPPER']
	bb_pct = daily['BB_PCT']
	bb_width = daily['BB_WIDTH']
	key = f'DASHBOARD:DATA:BBPCT:{symbol}'
	yfinance_dashboard_save(symbol, key, bb_pct)
	key = f'DASHBOARD:DATA:BBWIDTH:{symbol}'
	yfinance_dashboard_save(symbol, key, bb_width)
	macd_height = daily['MACD_HEIGHT']
	key = f'DASHBOARD:DATA:MACDHEIGHT:{symbol}'
	yfinance_dashboard_save(symbol, key, macd_height)

# edates_list looks something like this:
# ['2025-01-30']
# ['2025-01-31', '2025-02-04']
def yfinance_handle_new_stock_calendar(key, symbol):
	dtr_str = ''
	val = g_rc.get(key)
	edates_list = json.loads(val)
	now_et_str = datetime.datetime.now(g_tz_et).strftime('%Y-%m-%d')
	now_date = datetime.date.fromisoformat(now_et_str)
	for i,d in enumerate(edates_list):
		report_date = datetime.date.fromisoformat(d)
		diff = f'{report_date-now_date}'
		if diff == '0:00:00': diff_str = '0 days'
		else: diff_str = diff.split(',')[0]
		if (i == 0): dtr_str = diff_str
		else: dtr_str += f', {diff_str}'
	key = f'DASHBOARD:DATA:DAYSTILLREPORT:{symbol}'
	yfinance_dashboard_save(symbol, key, dtr_str)

def yfinance_handle_new_stock_info(key, symbol):
	val = g_rc.get(key)
	info = json.loads(val)
	if 'currentPrice' in info:
		val = info['currentPrice']
		key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'previousClose' in info:
		val = info['previousClose']
		key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'bookValue' in info:
		val = info['bookValue']
		key = f'DASHBOARD:DATA:BOOKVALUE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'forwardPE' in info:
		val = info['forwardPE']
		key = f'DASHBOARD:DATA:FORWARDPE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'trailingPegRatio' in info:
		val = info['trailingPegRatio']
		key = f'DASHBOARD:DATA:TRAILINGPEGRATIO:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'priceToSalesTrailing12Months' in info:
		val = info['priceToSalesTrailing12Months']
		key = f'DASHBOARD:DATA:PRICETOSALESTRAILING12MONTHS:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'sharesOutstanding' in info:
		val = info['sharesOutstanding']
		key = f'DASHBOARD:DATA:SHARESOUTSTANDING:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'marketCap' in info:
		val = info['marketCap']
		key = f'DASHBOARD:DATA:MARKETCAP:{symbol}'
		yfinance_dashboard_save(symbol, key, val)

def yfinance_handle_new_crypto_info(key, symbol):
	val = g_rc.get(key)
	info = json.loads(val)
	if 'previousClose' in info:
		val = info['previousClose']
		key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'circulatingSupply' in info:
		val = info['circulatingSupply']
		key = f'DASHBOARD:DATA:CIRCULATINGSUPPLY:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'marketCap' in info:
		val = info['marketCap']
		key = f'DASHBOARD:DATA:MARKETCAP:{symbol}'
		yfinance_dashboard_save(symbol, key, val)

def yfinance_handle_new_index_info(key, symbol):
	val = g_rc.get(key)
	info = json.loads(val)
	if 'bid' in info:
		val = info['bid']
		key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'previousClose' in info:
		val = info['previousClose']
		key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)

def yfinance_handle_new_future_info(key, symbol):
	val = g_rc.get(key)
	info = json.loads(val)
	if 'bid' in info:
		val = info['bid']
		key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'previousClose' in info:
		val = info['previousClose']
		key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)

def yfinance_handle_new_etf_info(key, symbol):
	val = g_rc.get(key)
	info = json.loads(val)
	if 'navPrice' in info:
		val = info['navPrice']
		key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)
	if 'previousClose' in info:
		val = info['previousClose']
		key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		yfinance_dashboard_save(symbol, key, val)

# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:DAILYINDICATORS:STOCK:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:CALENDAR:STOCK:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:INFO:CRYPTO:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:INFO:STOCK:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:INFO:INDEX:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:INFO:FUTURE:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:INFO:ETF:{symbol}'}
def handle_channel_message(p, msg_obj):
#	print(msg_obj['channel'])
	key = msg_obj['data']
	symbol = key.split(':')[3]
	if key.startswith('YFINANCE:INFO:ETF:'):
		yfinance_handle_new_etf_info(key, symbol)
	if key.startswith('YFINANCE:INFO:FUTURE:'):
		yfinance_handle_new_future_info(key, symbol)
	if key.startswith('YFINANCE:INFO:INDEX:'):
		yfinance_handle_new_index_info(key, symbol)
	if key.startswith('YFINANCE:INFO:CRYPTO:'):
		yfinance_handle_new_crypto_info(key, symbol)
	if key.startswith('YFINANCE:INFO:STOCK:'):
		yfinance_handle_new_stock_info(key, symbol)
	if key.startswith('YFINANCE:CALENDAR:STOCK:'):
		yfinance_handle_new_stock_calendar(key, symbol)
	if key.startswith('YFINANCE:DAILYINDICATORS:STOCK:'):
		yfinance_handle_new_stock_dailyindicators(key, symbol)

def channel_handler(p, msg_obj):
	if (msg_obj['type'] == 'message'):
		handle_channel_message(p, msg_obj)
	else:
		print(msg_obj, flush=True)

def acquire_environment():
	global g_debug_python

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return redis_url

if __name__ == "__main__":
	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	p = g_rc.pubsub()
	p.subscribe(f'SOURCE:YFINANCE:UPDATED')

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	while not g_shutdown:
		msg = p.get_message()
		if msg: channel_handler(p, msg)
		else: usleep(1000)
