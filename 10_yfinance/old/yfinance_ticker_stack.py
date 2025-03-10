#!/usr/bin/env python3

import os
import sys
import redis

from argparse import ArgumentParser

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False
g_ticker_stack_key = 'YFINANCE:STACK:INFOTICKER'

g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

# Acquire the complete set of symbols from redis
# Reload stack at g_ticker_stack_key to a set of all tickers
def reload_ticker_stack():
	stock_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:STOCKS')
	crypto_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')
	symbols_set = stock_set.union(crypto_set).union(index_set).union(etf_set).union(future_set)
	num_updated = g_rc.sadd(g_ticker_stack_key, *symbols_set)
	print(f'{g_ticker_stack_key} RELOADED: {num_updated} added', flush=True)

def pop_ticker():
	random_ticker = g_rc.spop(g_ticker_stack_key)
	while (random_ticker is None):
		reload_ticker_stack()
		random_ticker = g_rc.spop(g_ticker_stack_key)
	return random_ticker

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
	parser = ArgumentParser()
	parser.add_argument('--reload', '-r', required=False, action='store_true')
	parser.add_argument('--pop', '-p', required=False, action='store_true')
	args = parser.parse_args()

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	wait_for_ready(g_rc, 'DASHBOARD:READY', 0.1)

	if args.reset:
		load_ticker_stack()

	if args.pop:
		t = pop_ticker()
		if (t is not None): print(t)
