#!/usr/bin/env python3

import os
import sys
import pytz
import json
import redis

from datetime import datetime

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def calc_next(next):
	now_z = datetime.utcnow()
	next_et = datetime.strptime(next, '%Y-%m-%dT%H:%M:%S%z')
	next_z = next_et.astimezone(pytz.UTC)
	next_ts = next_z.timestamp()
	diff = next_ts - now_z.timestamp()
	diff_int = int(diff)
	return next_et,diff_int

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
	r = connect_to_redis(redis_url, True, False, g_debug_python)

	market_status_str = r.get('MARKET:STATUS')
	print(f'Stock Market is {market_status_str}')

	market_clock_str = r.get('MARKET:CLOCK')
	market_clock = json.loads(market_clock_str)
	next_open,diff_open = calc_next(market_clock['next_open'])
	next_close,diff_close = calc_next(market_clock['next_close'])

	if (diff_close < diff_open):
		print(f'Stock Market closess in {diff_close:>6}s @ {next_close}')
		print(f'Stock Market   opens in {diff_open:>6}s @ {next_open}')
	else:
		print(f'Stock Market   opens in {diff_open:>6}s @ {next_open}')
		print(f'Stock Market closess in {diff_close:>6}s @ {next_close}')
