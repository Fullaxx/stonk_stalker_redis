#!/usr/bin/env python3

import os
import sys
import time
import redis
import signal

from datetime import datetime

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False
g_request_interval = 15
g_wait_for_ready = True

g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def acquire_environment():
	global g_request_interval, g_wait_for_ready, g_debug_python

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	ri_str = os.getenv('YFINANCE_REQUEST_INTERVAL')
	g_request_interval = 15 if ri_str is None else int(ri_str)

	swfr_env_var = os.getenv('WAIT_FOR_READY')
	if swfr_env_var is not None:
		flags = ('0', 'n', 'N', 'f', 'F')
		if (swfr_env_var.startswith(flags)): g_wait_for_ready = False
		if (swfr_env_var == 'off'): g_wait_for_ready = False
		if (swfr_env_var == 'OFF'): g_wait_for_ready = False

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

	if g_wait_for_ready:
		wait_for_ready(r, 'DASHBOARD:READY', 0.1)

#	Acquire the set of symbols from redis
	stock_set = r.smembers('DASHBOARD:SYMBOLS_SET:STOCKS')
	crypto_set = r.smembers('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_set = r.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = r.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = r.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')
	symbols_set = stock_set.union(crypto_set).union(index_set).union(etf_set).union(future_set)

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

#	While we are looping pop a symbol from loop_set and pass it to /app/ticker2redis.py
#	Whenever loop_set becomes empty, copy symbols_set back into loop_set and start over
	next = 0
	loop_set = set()
	while not g_shutdown:
		if (len(loop_set) == 0):
			loop_set = symbols_set.copy()
		now_dt = datetime.utcnow()
		now_s = int(now_dt.timestamp())
		if (now_s >= next):
			symbol = loop_set.pop()
			os.system(f'/app/ticker2redis.py -s {symbol}')
			next = now_s + g_request_interval
		time.sleep(0.1)
