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

import time
usleep = lambda x: time.sleep(x/1000000.0)

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,is_market_open

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

def alpaca_dashboard_save_currentprice(symbol, cp):
#	Dont update current price during extended hours
	if not g_market_is_open: return

	key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
	result = g_rc.set(key, cp)
	if result:
		print(f'SET {key:<20} ${cp}', flush=True)
	else:
		eprint(f'SET {key:<20} FAILED!')

def alpaca_handle_new_trade(key, symbol):
	val = g_rc.get(key)
	trade = json.loads(val)
	price = trade['p']
	alpaca_dashboard_save_currentprice(symbol, price)

# We are ignoring quotes at the moment
def alpaca_handle_new_quote(key, symbol):
	val = g_rc.get(key)
	quote = json.loads(val)
	bid_price = quote['bp']
	ask_price = quote['ap']
#	alpaca_dashboard_save_currentprice(symbol, bid_price)

def alpaca_handle_new_1minbar(key, symbol):
	val = g_rc.get(key)
	bar = json.loads(val)
	cp = bar['c']
	alpaca_dashboard_save_currentprice(symbol, cp)

# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:ALPACA:UPDATED',   'data': 'ALPACA:TRADE:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:ALPACA:UPDATED',   'data': 'ALPACA:QUOTE:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:ALPACA:UPDATED',   'data': 'ALPACA:1MINBARS:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:ALPACA:UPDATED',   'data': 'ALPACA:DAILYBARS:{symbol}'}
def handle_channel_message(msg_obj):
#	print(msg_obj['channel'])
	key = msg_obj['data']
	symbol = key.split(':')[2]
	if key.startswith('ALPACA:1MINBARS:'):
		alpaca_handle_new_1minbar(key, symbol)
	if key.startswith('ALPACA:QUOTE:'):
		alpaca_handle_new_quote(key, symbol)
	if key.startswith('ALPACA:TRADE:'):
		alpaca_handle_new_trade(key, symbol)

def channel_handler(msg_obj):
	if (msg_obj['type'] == 'message'):
		handle_channel_message(msg_obj)
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

if __name__ == '__main__':
	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	g_market_is_open = is_market_open(g_rc, 0.1)

	p = g_rc.pubsub()
	p.subscribe(f'SOURCE:ALPACA:UPDATED')

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	g_last_sec_trigger = 0
	while not g_shutdown:
		g_now_z = datetime.datetime.now(datetime.timezone.utc)
		g_now_s = int(g_now_z.timestamp())
		if (g_now_s > g_last_sec_trigger):
			g_market_is_open = is_market_open(g_rc, 0.1)
			g_last_sec_trigger = g_now_s

		msg = p.get_message()
		if msg: channel_handler(msg)
		else: usleep(1000)
