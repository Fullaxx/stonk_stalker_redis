#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import time
import redis
import signal

from datetime import datetime
from contextlib import suppress

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False
g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def write_to_file(text, filename):
	with open(filename, 'w') as f:
		f.write(text)
		f.close()

def prepare_marketdb(r):
	marketdb = {}
	symb_set = r.smembers('SSCFG:SYMBOLSET')
	for symbol in symb_set:
		am_min_bar_str = r.get(f'ALPACA:1MINBARS:{symbol}')
		yf_info_str = r.get(f'YFINANCE:INFO:{symbol}')
		if am_min_bar_str is None:
			eprint(f'GET ALPACA:1MINBARS:{symbol} FAILED!')
			continue
		if yf_info_str is None:
			eprint(f'GET YFINANCE:INFO:{symbol} FAILED!')
			continue

		am_min_bar = json.loads(am_min_bar_str)
		yf_info = json.loads(yf_info_str)
		if 'pegRatio' not in yf_info: yf_info['pegRatio'] = ''
		if 'priceToSalesTrailing12Months' not in yf_info: yf_info['priceToSalesTrailing12Months'] = ''
		marketdb[symbol] = {
			'currentPrice':am_min_bar['c'],
			'pegRatio':yf_info['pegRatio'],
			'forwardPE':yf_info['forwardPE'],
			'marketCap':yf_info['marketCap'],
			'previousClose':yf_info['previousClose'],
			'priceToSalesTrailing12Months':yf_info['priceToSalesTrailing12Months']
		}
	return marketdb

def dump_marketdb(r, now_dt, filename):
	marketdb = prepare_marketdb(r)
	market_str = json.dumps(marketdb)
	print(f'{now_dt} Writing {filename} ...', flush=True)
	write_to_file(market_str, filename)

def acquire_environment():
	global g_debug_python

	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)
	with suppress(FileExistsError): os.mkdir('market_data')
	os.chdir('market_data')

	if os.getenv('REDIS_URL') is None: bailmsg('Set REDIS_URL')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

if __name__ == '__main__':
	acquire_environment()
	r = connect_to_redis(os.getenv('REDIS_URL'), True, False, g_debug_python)

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	next = 0
	filename = f'market.json'
	while not g_shutdown:
		now_dt = datetime.utcnow()
		now_s = int(now_dt.timestamp())
		if (now_s >= next):
			dump_marketdb(r, now_dt, filename)
			next = now_s + 15
		time.sleep(0.1)
