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
from ss_cfg import get_dashboard_ready_key,get_symbols_set_key
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False
g_market_json_creation_interval = 5


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

def prepare_symbol(r, symbol):
	fsymb = symbol.replace('/','-')
#	What happenes if we default these to NULL?
	symb_dict = {
		'symbol':fsymb,
		'dtr':'',
		'bookValue':'',
		'forwardPE':'',
		'marketCap':'',
		'currentPrice':'',
		'previousClose':'',
		'trailingPegRatio':'',
		'priceToSalesTrailing12Months':''
	}

#	Reformat DTR string
	dtr = r.get(f'DASHBOARD:DATA:DAYSTILLREPORT:{symbol}')
	if dtr is not None:
		first_only = dtr.split(',')[0]
		dtr_formatted = first_only.replace(' days', 'd').replace(' day', 'd')
		symb_dict['dtr'] = dtr_formatted

#	FPE needs to be represented as a string, due to possible inf??
	forwardPE = r.get(f'SS:LIVE:FORWARDPE:{symbol}')
	if forwardPE is not None:
		fval = float(forwardPE)
		fpe_str = '%.2f' % round(fval, 2)
		symb_dict['forwardPE'] = fpe_str

	currentPrice = r.get(f'SS:LIVE:CURRENTPRICE:{symbol}')
	if currentPrice is not None: symb_dict['currentPrice'] = float(currentPrice)
	previousClose = r.get(f'SS:LIVE:PREVIOUSCLOSE:{symbol}')
	if previousClose is not None: symb_dict['previousClose'] = float(previousClose)
	marketCap = r.get(f'SS:LIVE:MARKETCAP:{symbol}')
	if marketCap is not None: symb_dict['marketCap'] = float(marketCap)
	bookValue = r.get(f'SS:LIVE:BOOKVALUE:{symbol}')
	if bookValue is not None: symb_dict['bookValue'] = float(bookValue)
	trailingPegRatio = r.get(f'SS:LIVE:TRAILINGPEGRATIO:{symbol}')
	if trailingPegRatio is not None: symb_dict['trailingPegRatio'] = float(trailingPegRatio)
	priceToSalesTrailing12Months = r.get(f'SS:LIVE:PRICETOSALESTRAILING12MONTHS:{symbol}')
	if priceToSalesTrailing12Months is not None: symb_dict['priceToSalesTrailing12Months'] = float(priceToSalesTrailing12Months)

	return symb_dict

def prepare_marketdb(r):
	marketdb = {}
	key = get_symbols_set_key()
	symb_set = r.smembers(key)
	for symbol in symb_set:
		marketdb[symbol] = prepare_symbol(r, symbol)
	return marketdb

def dump_marketdb(r, now_dt, filename):
	marketdb = prepare_marketdb(r)
	market_str = json.dumps(marketdb)
	print(f'{now_dt} Writing {filename} ...', flush=True)
	write_to_file(market_str, filename)

def prepare_marketlist(r):
	marketlist = []
	key = get_symbols_set_key()
	symb_set = r.smembers(key)
	for symbol in symb_set:
		symbol_obj = prepare_symbol(r, symbol)
		marketlist.append(symbol_obj)
	return marketlist

def dump_marketlist(r, now_dt, filename):
	marketlist = prepare_marketlist(r)
	market_str = json.dumps(marketlist)
	print(f'{now_dt} Writing {filename} ...', flush=True)
	write_to_file(market_str, filename)

def acquire_environment():
	global g_market_json_creation_interval, g_debug_python

	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)
	with suppress(FileExistsError): os.mkdir('market_data')
	os.chdir('market_data')

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	env_val = os.getenv('MARKET_DATA_CREATE_INTERVAL')
	if env_val is not None: g_market_json_creation_interval = int(env_val)

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

	key = get_dashboard_ready_key()
	wait_for_ready(r, key, 0.1)

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	next = 0
	while not g_shutdown:
		now_dt = datetime.utcnow()
		now_s = int(now_dt.timestamp())
		if (now_s >= next):
			dump_marketdb(r, now_dt, f'marketdb.json')
			dump_marketlist(r, now_dt, f'marketlist.json')
			next = now_s + g_market_json_creation_interval
		time.sleep(0.1)
