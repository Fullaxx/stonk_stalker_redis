#!/usr/bin/env python3
# pip3 install redis,yfinance

import os
import sys
import json
import redis

import yfinance as yf
from pprint import pprint
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

def delete_if_exists(info_d, key):
	if key in info_d:
		del info_d[key]

def publish_message(r, symbol, key):
#	Publish a message indicating an update to specified symbol
	channel = f'SOURCE:YFINANCE:UPDATED'
	message = f'{key}'
	r.publish(channel, message)

def save_crypto_info(r, symbol, info):
	info_str = json.dumps(info)
	key = f'YFINANCE:INFO:CRYPTO:{symbol}'
	result = r.set(key, info_str)
	if result:
		print(f'SET {key:<32}')
		publish_message(r, symbol, key)
	else:
		eprint(f'SET {key:<32} FAILED!')

def save_stock_info(r, symbol, info):
	delete_if_exists(info, 'companyOfficers')
	delete_if_exists(info, 'longBusinessSummary')
	cp = info['currentPrice'] if 'currentPrice' in info else 0
	info_str = json.dumps(info)
	key = f'YFINANCE:INFO:STOCK:{symbol}'
	result = r.set(key, info_str)
	if result:
		print(f'SET {key:<28} ${cp}')
		publish_message(r, symbol, key)
	else:
		eprint(f'SET {key:<28} FAILED!')

def save_stock_calendar(r, symbol, calendar):
	if g_debug_python: pprint(calendar)
	if 'Earnings Date' not in calendar: return

	edates_list = []
	earnings_date_array = calendar['Earnings Date']
	for e in earnings_date_array:
		edates_list.append(f'{e}')

	edates_str = json.dumps(edates_list)
	key = f'YFINANCE:CALENDAR:STOCK:{symbol}'
	result = r.set(key, edates_str)
	if result:
		print(f'SET {key:<28} {edates_str}')
		publish_message(r, symbol, key)
	else:
		eprint(f'SET {key:<28} FAILED!')
#	print(edates_str)

def save_index_info(r, symbol, info):
	bid = info['bid'] if 'bid' in info else 0
	info_str = json.dumps(info)
	key = f'YFINANCE:INFO:INDEX:{symbol}'
	result = r.set(key, info_str)
	if result:
		print(f'SET {key:<28} ${bid}')
		publish_message(r, symbol, key)
	else:
		eprint(f'SET {key:<28} FAILED!')

def save_future_info(r, symbol, info):
	bid = info['bid'] if 'bid' in info else 0
	info_str = json.dumps(info)
	key = f'YFINANCE:INFO:FUTURE:{symbol}'
	result = r.set(key, info_str)
	if result:
		print(f'SET {key:<28} ${bid}')
		publish_message(r, symbol, key)
	else:
		eprint(f'SET {key:<28} FAILED!')

def save_etf_info(r, symbol, info):
#	navPrice = info['navPrice'] if 'navPrice' in info else 0
	bid = info['bid'] if 'bid' in info else 0
	info_str = json.dumps(info)
	key = f'YFINANCE:INFO:ETF:{symbol}'
	result = r.set(key, info_str)
	if result:
		print(f'SET {key:<28} ${bid}')
		publish_message(r, symbol, key)
	else:
		eprint(f'SET {key:<28} FAILED!')

# res.info['quoteType'] == INDEX|FUTURE|ETF|EQUITY|CRYPTOCURRENCY
def process_yfinance_response(r, symbol, res):
	info = res.info
	if info is None:
		eprint(f'{symbol} has no info!')
		return

	if res.info['quoteType'] == 'ETF':
		save_etf_info(r, symbol, info)
	if res.info['quoteType'] == 'FUTURE':
		save_future_info(r, symbol, info)
	if res.info['quoteType'] == 'INDEX':
		save_index_info(r, symbol, info)
	if res.info['quoteType'] == 'CRYPTOCURRENCY':
		save_crypto_info(r, symbol, info)
	if res.info['quoteType'] == 'EQUITY':
		save_stock_info(r, symbol, info)
		save_stock_calendar(r, symbol, res.calendar)

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
	parser.add_argument('--symbol', '-s', type=str, required=True)
	args = parser.parse_args()

	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)
	yf_symbol = args.symbol.replace('/','-')
	res = yf.Ticker(yf_symbol)
	process_yfinance_response(r, args.symbol, res)
