#!/usr/bin/env python3
# pip3 install redis,yfinance

import os
import sys
import json
import time
import redis
import yfinance as yf

sys.path.append('.')
sys.path.append('/app')
from ss_cfg import get_dashboard_ready_key,get_symbols_set_key,read_ss_config
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def save_symbols(r, symbols_str):
	key = get_symbols_set_key()
	symbols_list = symbols_str.split(',')
	num_updated = r.sadd(key, *symbols_list)
	print(f'{key} {symbols_list}: {num_updated}', flush=True)

def get_mcap_value_yf(symbol):
	retval = 0
	symbol = symbol.replace('/','-')
	try:
		res = yf.Ticker(symbol)
	except:
		pass
	else:
		if 'marketCap' in res.info:
			retval = res.info['marketCap']
		else:
			eprint(f'{symbol} has no marketCap object')

	return retval

# Attempt to get mcap from redis first
# If it doesnt exist, query yfinance for mcap
def get_mcap_value(r, symbol):
	key = f'SS:LIVE:MARKETCAP:{symbol}'
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

def process_table(r, k, v):
#	Default True, later read this from config
	sort_tables_by_mcap = True

	table_name = v['TABLENAME']
	symbols_str = v['SYMBOLS']
	save_symbols(r, symbols_str)
	if sort_tables_by_mcap:
		sort_table_by_mcap_and_save(r, table_name, symbols_str)

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

#	Delete the set and re-create
	key = get_symbols_set_key()
	r.delete(key)

#	Read the config and create a SET of symbols
	ss_config = read_ss_config()
	for k,v in ss_config.items():
		if k.startswith('TABLE_'):
			process_table(r, k, v)

#	Inform others that we are ready
	key = get_dashboard_ready_key()
	r.set(key, 'READY', ex=10)
	print(f'READY!', flush=True)

#	Sleep for a bit so supervisord knows all is well
	time.sleep(3)
