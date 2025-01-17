#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import redis

from argparse import ArgumentParser

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def update_prevclose(symbols_set):
	for s in symbols_set:
		key = f'DASHBOARD:DATA:CURRENTPRICE:{s}'
		cp = g_rc.get(key)
		if cp is None: continue
		prev_close_key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{s}'
		print(f'Setting {prev_close_key:<40} ${cp}', flush=True)
		g_rc.set(prev_close_key, cp)

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
	parser.add_argument('--crypto', '-c', required=False, default=False, action='store_true')
	args = parser.parse_args()

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)

#	CRYPTO has no market close, and a 24 hr 'day'
#	Which means their PREVIOUSCLOSE must be handled differently
	crypto_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:CRYPTO')
	if args.crypto:
		update_prevclose(crypto_set)
		sys.exit(0)

#	Everything else runs on the NYSE market clock
	stock_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:STOCKS')
	index_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')
	symbols_set = stock_set.union(index_set).union(etf_set).union(future_set)
	update_prevclose(symbols_set)
