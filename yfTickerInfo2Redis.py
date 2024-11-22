#!/usr/bin/env python3
# pip3 install redis,yfinance

import os
import sys
import json
import redis

import yfinance as yf
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

def push_info_to_redis(r, symbol, info):
	cp = info['currentPrice']
	info_str = json.dumps(info)
	key = f'YFINANCE:INFO:{symbol}'
	result = r.set(key, info_str)
	if result:
		print(f'SET {key} ${cp}')
	else:
		print(f'SET {key} FAIED!')

def delete_if_exists(stock_d, key):
	if key in stock_d:
		del stock_d[key]

def acquire_environment():
	global g_debug_python

	if os.getenv('REDIS_URL') is None: bailmsg('Set REDIS_URL')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('--symbol', '-s', type=str, required=True)
	args = parser.parse_args()

	acquire_environment()
	r = connect_to_redis(os.getenv('REDIS_URL'), True, g_debug_python)
	res = yf.Ticker(args.symbol)

	delete_if_exists(res.info, 'companyOfficers')
	delete_if_exists(res.info, 'longBusinessSummary')
	push_info_to_redis(r, args.symbol, res.info)
