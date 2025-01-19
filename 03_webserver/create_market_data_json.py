#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import redis
#import datetime

from contextlib import suppress

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

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

def prepare_symbol(symbol):
	nan_flags = ('n', 'N')
	yfsymb = symbol.replace('/','-')
#	What happenes if we default these to NULL?
	symb_dict = {
		'symbol':yfsymb,
		'dtr':'',
		'bookValue':'',
		'forwardPE':'',
		'marketCap':'',
		'currentPrice':'',
		'lastYearClose':'',
		'previousClose':'',
		'trailingPegRatio':'',
		'priceToSalesTrailing12Months':''
	}

#	Reformat DTR string
	dtr = g_rc.get(f'DASHBOARD:DATA:DAYSTILLREPORT:{symbol}')
	if dtr is not None:
		first_only = dtr.split(',')[0]
		dtr_formatted = first_only.replace(' days', 'd').replace(' day', 'd')
		symb_dict['dtr'] = dtr_formatted

#	FPE needs to be represented as a string, due to possible inf??
	forwardPE = g_rc.get(f'DASHBOARD:DATA:FORWARDPE:{symbol}')
	if forwardPE is not None:
		fval = float(forwardPE)
		fpe_str = '%.2f' % round(fval, 2)
		symb_dict['forwardPE'] = fpe_str

	currentPrice = g_rc.get(f'DASHBOARD:DATA:CURRENTPRICE:{symbol}')
	if currentPrice is not None:
		if (not currentPrice.startswith(nan_flags)):
			symb_dict['currentPrice'] = float(currentPrice)

	marketCap = g_rc.get(f'DASHBOARD:DATA:MARKETCAP:{symbol}')
	if marketCap is not None: symb_dict['marketCap'] = float(marketCap)
	bookValue = g_rc.get(f'DASHBOARD:DATA:BOOKVALUE:{symbol}')
	if bookValue is not None: symb_dict['bookValue'] = float(bookValue)
	lastYearClose = g_rc.get(f'DASHBOARD:DATA:LASTYEARCLOSE:{symbol}')
	if lastYearClose is not None: symb_dict['lastYearClose'] = float(lastYearClose)
	previousClose = g_rc.get(f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}')
	if previousClose is not None: symb_dict['previousClose'] = float(previousClose)
	trailingPegRatio = g_rc.get(f'DASHBOARD:DATA:TRAILINGPEGRATIO:{symbol}')
	if trailingPegRatio is not None: symb_dict['trailingPegRatio'] = float(trailingPegRatio)
	priceToSalesTrailing12Months = g_rc.get(f'DASHBOARD:DATA:PRICETOSALESTRAILING12MONTHS:{symbol}')
	if priceToSalesTrailing12Months is not None: symb_dict['priceToSalesTrailing12Months'] = float(priceToSalesTrailing12Months)

	return symb_dict

def prepare_marketdb():
	marketdb = {}
	stock_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:STOCKS')
	crypto_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')
	symbols_set = stock_set.union(crypto_set).union(index_set).union(etf_set).union(future_set)
	for symbol in symbols_set:
		marketdb[symbol] = prepare_symbol(symbol)
	return marketdb

def dump_marketdb(filename):
	marketdb = prepare_marketdb()
	market_str = json.dumps(marketdb)
#	print(f'{now_dt} Writing {filename} ...', flush=True)
	write_to_file(market_str, filename)

def prepare_marketlist():
	marketlist = []
	stock_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:STOCKS')
	crypto_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')
	symbols_set = stock_set.union(crypto_set).union(index_set).union(etf_set).union(future_set)
	for symbol in symbols_set:
		symbol_obj = prepare_symbol(symbol)
		marketlist.append(symbol_obj)
	return marketlist

def dump_marketlist(filename):
	marketlist = prepare_marketlist()
	market_str = json.dumps(marketlist)
#	print(f'{now_dt} Writing {filename} ...', flush=True)
	write_to_file(market_str, filename)

def acquire_environment():
	global g_debug_python

	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)
	with suppress(FileExistsError): os.mkdir('market_data')
	os.chdir('market_data')

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
#	g_today = datetime.datetime.today()
#	g_last_year = g_today.year - 1
#	if ((g_today.month == 1) and (g_today.day == 1)): g_last_year = g_today.year - 2

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	wait_for_ready(g_rc, 'DASHBOARD:READY', 0.1)

#	dump_marketdb(f'marketdb.json')
	dump_marketlist(f'marketlist.json')
