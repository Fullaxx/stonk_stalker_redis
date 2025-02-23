#!/usr/bin/env python3
# pip3 install redis,yfinance

import os
import sys
import json
import redis

import yfinance as yf

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def get_mcap_value_yf(symbol):
	retval = 0
	yf_symbol = symbol.replace('/','-')
	try:
		res = yf.Ticker(yf_symbol)
	except:
		pass
	else:
		if 'marketCap' in res.info:
			retval = res.info['marketCap']
		else:
			eprint(f'{yf_symbol} has no marketCap object')

	return retval

# Attempt to get mcap from redis first
# If it doesnt exist, query yfinance for mcap
def get_mcap_value(r, symbol):
	key = f'DASHBOARD:DATA:MARKETCAP:{symbol}'
	mcap_val = r.get(key)
	if mcap_val is not None:
		return int(mcap_val)
	return get_mcap_value_yf(symbol)

def sort_list_by_mcap(r, symbols_list):
	mcap_list = []
	mcap_dict = {}

	for symbol in symbols_list:
#		print(f'Gathering financials for {symbol} ...')
		mcap = get_mcap_value(r, symbol)
		if mcap is not None:
			mcap_list.append(mcap)
			mcap_dict[str(mcap)] = symbol
	mcap_list.sort(reverse=True)

	sorted_str = ''
	for i,m in enumerate(mcap_list):
		symbol = mcap_dict[str(m)]
		if (i != 0): sorted_str += ','
		sorted_str += f'{symbol}'

	return sorted_str

def sort_table_by_mcap_and_save(r, table_name, symbols_str):
	symbols_list = symbols_str.split(',')
	sorted_str = sort_list_by_mcap(r, symbols_list)
	print(f'{table_name:<12} {sorted_str}')
	key = f'DASHBOARD:TABLES:SORTED:MCAP:{table_name}'
	r.set(key, sorted_str)

def save_index_table(r, table_name, symbols_str):
	print(f'{table_name:<12} {symbols_str}')
	key = f'DASHBOARD:TABLES:INDEX:{table_name}'
	r.set(key, symbols_str)

def save_future_table(r, table_name, symbols_str):
	print(f'{table_name:<12} {symbols_str}')
	key = f'DASHBOARD:TABLES:FUTURE:{table_name}'
	r.set(key, symbols_str)

def save_etf_table(r, table_name, symbols_str):
	print(f'{table_name:<12} {symbols_str}')
	key = f'DASHBOARD:TABLES:ETF:{table_name}'
	r.set(key, symbols_str)

def save_symbols(r, table_type, key, symbols_str):
	symbols_list = symbols_str.split(',')
	num_updated = r.sadd(key, *symbols_list)
	print(f'{key} {symbols_list}: {num_updated}', flush=True)

def process_table(r, k, v):
#	Default True, later read this from config
	sort_tables_by_mcap = True

	table_name = v['TABLENAME']
	table_type = v['TABLETYPE']
	symbols_str = v['SYMBOLS']

	if (table_type == 'index'):
		set_key = 'DASHBOARD:SYMBOLS_SET:INDEX'
		save_index_table(r, table_name, symbols_str)
	if (table_type == 'future'):
		set_key = 'DASHBOARD:SYMBOLS_SET:FUTURE'
		save_future_table(r, table_name, symbols_str)
	if (table_type == 'etf'):
		set_key = 'DASHBOARD:SYMBOLS_SET:ETF'
		save_etf_table(r, table_name, symbols_str)
	if (table_type == 'crypto'):
		set_key = 'DASHBOARD:SYMBOLS_SET:CRYPTO'
		if sort_tables_by_mcap:
			sort_table_by_mcap_and_save(r, table_name, symbols_str)
	if (table_type == 'stock'):
		set_key = 'DASHBOARD:SYMBOLS_SET:STOCKS'
		if sort_tables_by_mcap:
			sort_table_by_mcap_and_save(r, table_name, symbols_str)

	if set_key is None:
		bailmsg('table_type must be index/etf/future/stock/crypto!')

	save_symbols(r, table_type, set_key, symbols_str)

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

#	Delete the set(s) and re-create
	searchpattern = f'DASHBOARD:SYMBOLS_SET:*'
	for key in sorted(r.scan_iter(searchpattern)):
		r.delete(key)

#	Delete all the tables and recreate
	searchpattern = f'DASHBOARD:TABLES:*'
	for key in sorted(r.scan_iter(searchpattern)):
		r.delete(key)

#	Read the config and create a SET of symbols
	cfg_str = r.get('DASHBOARD:CONFIG')
	ss_config = json.loads(cfg_str)
	for k,v in ss_config.items():
		if k.startswith('TABLE_'):
			process_table(r, k, v)
