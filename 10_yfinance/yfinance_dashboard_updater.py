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
import time
import json
#import pytz
import redis
import signal
import datetime

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_shutdown = False
g_debug_python = False

usleep = lambda x: time.sleep(x/1000000.0)

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def yfinance_dashboard_save(r, symbol, key, val):
	if val is None:
		eprint(f'{key} has NULL vlaue - NOT SETTING!')
		return

	result = r.set(key, val)
	if result:
		print(f'SET {key:<20} {val}', flush=True)
	else:
		eprint(f'SET {key:<20} FAILED!')

def yfinance_handle_new_stock_calendar(r, key, symbol):
	dtr_str = ''
	val = r.get(key)
	edates_list = json.loads(val)
	now = datetime.date.today()
	for i,d in enumerate(edates_list):
		dt_obj = datetime.date.fromisoformat(d)
		diff = f'{dt_obj-now}'
		if diff == '0:00:00': diff_str = "0 days"
		else: diff_str = diff.split(',')[0]
		if (i == 0): dtr_str = diff_str
		else: dtr_str += f', {diff_str}'
	print(dtr_str)
	key = f'DASHBOARD:DATA:DAYSTILLREPORT:{symbol}'
	yfinance_dashboard_save(r, symbol, key, dtr_str)

def yfinance_handle_new_stock_info(r, key, symbol):
	val = r.get(key)
	info = json.loads(val)
	if 'currentPrice' in info:
		val = info['currentPrice']
		key = f'SS:LIVE:CURRENTPRICE:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)
	if 'previousClose' in info:
		val = info['previousClose']
		key = f'SS:LIVE:PREVIOUSCLOSE:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)
	if 'marketCap' in info:
		val = info['marketCap']
		key = f'SS:LIVE:MARKETCAP:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)
	if 'bookValue' in info:
		val = info['bookValue']
		key = f'SS:LIVE:BOOKVALUE:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)
	if 'forwardPE' in info:
		val = info['forwardPE']
		key = f'SS:LIVE:FORWARDPE:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)
	if 'trailingPegRatio' in info:
		val = info['trailingPegRatio']
		key = f'SS:LIVE:TRAILINGPEGRATIO:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)
	if 'priceToSalesTrailing12Months' in info:
		val = info['priceToSalesTrailing12Months']
		key = f'SS:LIVE:PRICETOSALESTRAILING12MONTHS:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)

def yfinance_handle_new_crypto_info(r, key, symbol):
	val = r.get(key)
	info = json.loads(val)
	if 'previousClose' in info:
		val = info['previousClose']
		key = f'SS:LIVE:PREVIOUSCLOSE:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)
	if 'marketCap' in info:
		val = info['marketCap']
		key = f'SS:LIVE:MARKETCAP:{symbol}'
		yfinance_dashboard_save(r, symbol, key, val)

# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:INFO:CRYPTO:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:YFINANCE:UPDATED', 'data': 'YFINANCE:INFO:STOCK:{symbol}'}
def handle_channel_message(r, p, msg_obj):
#	print(msg_obj['channel'])
	key = msg_obj['data']
	symbol = key.split(':')[3]
	if key.startswith('YFINANCE:INFO:CRYPTO:'):
		yfinance_handle_new_crypto_info(r, key, symbol)
	if key.startswith('YFINANCE:INFO:STOCK:'):
		yfinance_handle_new_stock_info(r, key, symbol)
	if key.startswith('YFINANCE:CALENDAR:STOCK:'):
		yfinance_handle_new_stock_calendar(r, key, symbol)

def channel_handler(r, p, msg_obj):
	if (msg_obj['type'] == 'message'):
		handle_channel_message(r, p, msg_obj)
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
	r = connect_to_redis(redis_url, True, False, g_debug_python)
	p = r.pubsub()
	p.subscribe(f'SOURCE:YFINANCE:UPDATED')

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	while not g_shutdown:
		msg = p.get_message()
		if msg: channel_handler(r, p, msg)
		else: usleep(1000)
