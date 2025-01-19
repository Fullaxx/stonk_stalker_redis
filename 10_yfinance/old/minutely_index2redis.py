#!/usr/bin/env python3
# pip3 install redis,pandas,yfinance

import os
import sys
import redis
import datetime

import pandas as pd
import yfinance as yf

from argparse import ArgumentParser

import pytz
#g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def save_close_as_currentprice(s, c, z):
	d = datetime.datetime.fromtimestamp(z, tz=g_tz_et)
	print(f'{s:<5} ${c:<9} @ {d}')
	g_rc.set(f'DASHBOARD:DATA:CURRENTPRICE:{s}', c)

def process_symbol(df, s):
	z = df.index[-1].strftime('%s')
	last_row = df.iloc[-1]
	c = last_row['Close']
	save_close_as_currentprice(s, c, int(z))

def process_pickle(pickle_filename, symbols_list):
	ticker = pd.read_pickle(pickle_filename)
	for s in symbols_list:
		df = ticker[s].round(decimals=2).dropna()
		process_symbol(df, s)

def download_pickle(table_name, symbols_list):
	pickle_filename = f'{table_name}.1m.pickle'
	yfdata = yf.download(symbols_list, period='1d', interval='1m', group_by='ticker', progress=False, prepost=False)
	yfdata.to_pickle(pickle_filename)
	return pickle_filename

def process_indices(symbols_list):
	pickle_filename = download_pickle('indices', symbols_list)
	process_pickle(pickle_filename, symbols_list)
	os.remove(pickle_filename)

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
#	parser = ArgumentParser()
#	parser.add_argument('--year', '-y', type=int, required=True)
#	args = parser.parse_args()
#	g_year = args.year

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)

#	Why can't these be combined?
	index_list = ['^DJI', '^GSPC', '^IXIC', '^RUT']
	process_indices(index_list)

	index_list = ['^VIX']
	process_indices(index_list)