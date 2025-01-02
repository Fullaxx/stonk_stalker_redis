#!/usr/bin/env python3
# https://docs.alpaca.markets/reference/getclock-1

import os
import sys
import json
import redis
import signal
import datetime
import requests

import pytz
g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

import time
usleep = lambda x: time.sleep(x/1000000.0)

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_shutdown = False
g_debug_python = False

def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def set_market_status(r, json_str):
	print(json_str, flush=True)
	json_obj = json.loads(json_str)
	status_text = 'open' if json_obj['is_open'] else 'closed'
	r.set('MARKET:CLOCK', json_str)
	r.set('MARKET:STATUS', status_text)

# ENDPOINT: https://paper-api.alpaca.markets/v2/clock
# ENDPOINT: https://api.alpaca.markets/v2/clock
def check_market_status():
#	baseurl = 'https://api.alpaca.markets'
	baseurl = 'https://paper-api.alpaca.markets'
	clock_url = f'{baseurl}/v2/clock'

	headers = {'accept': 'application/json'}
	headers['APCA-API-KEY-ID'] = g_alpaca_apikey
	headers['APCA-API-SECRET-KEY'] = g_alpaca_secret

	try:
		response = requests.get(clock_url, headers=headers)
	except Exception as e:
		timestamp = datetime.datetime.now(g_tz_et).strftime('%y%m%d-%H%M%S')
		eprint(timestamp, e)
	else:
		if g_debug_python:
			print(response.text, flush=True)
		return response.text

#	if Exception was caught
	return None

def every_30min(r):
	json_resp = check_market_status()
	if (json_resp is not None):
		set_market_status(r, json_resp)

def acquire_environment():
	global g_alpaca_apikey, g_alpaca_secret, g_debug_python

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	g_alpaca_apikey = os.getenv('ALPACA_APIKEY')
	g_alpaca_secret = os.getenv('ALPACA_SECRET')
	if g_alpaca_apikey is None: bailmsg('Set ALPACA_APIKEY')
	if g_alpaca_secret is None: bailmsg('Set ALPACA_SECRET')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return redis_url

if __name__ == '__main__':
	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	every_30min(r)

	last_trigger = 0
	while not g_shutdown:
		now_dt = datetime.datetime.now(g_tz_utc)
		now_s = int(now_dt.timestamp())
		if ((now_s % (30*60)) == 0):
			if (now_s > last_trigger):
				every_30min(r)
				last_trigger = now_s
		usleep(1000)
