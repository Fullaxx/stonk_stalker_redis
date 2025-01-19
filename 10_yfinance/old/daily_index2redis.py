#!/usr/bin/env python3
# pip3 install redis,pandas,yfinance

import os
import sys
import redis

import pandas as pd
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

#def save_daily_close(s, c):
#	g_rc.set(f'DASHBOARD:DATA:CURRENTPRICE:{s}', c)

def save_year_open(s, o):
	g_rc.set(f'DASHBOARD:DATA:YEAROPEN:{s}', o)

#2024 ^DJI   37566.22 ->  42573.73 = +13.33%
#2024 ^GSPC    4745.2 ->   5906.94 = -24.24%
#2024 ^IXIC   14873.7 ->  19486.79 = - 7.77%
#2024 ^RUT    2012.75 ->   2227.78 = + 9.09%
def format_gain_loss_2(pct_change):
	gain_loss = round(pct_change, 2)
	gain_loss_str = ''
	if (pct_change > 0):
		gain_loss_str += '+'
		gain_loss = pct_change
	if (pct_change < 0):
		gain_loss_str += '-'
		gain_loss = abs(pct_change)

	gain_loss_str += f'{gain_loss:5.02f}%'
	return gain_loss_str

#2024 ^DJI   37566.22 ->  42573.73 = +13.33%
#2024 ^GSPC    4745.2 ->   5906.94 = -24.24%
#2024 ^IXIC   14873.7 ->  19486.79 =  -7.77%
#2024 ^RUT    2012.75 ->   2227.78 =  +9.09%
def format_gain_loss_1(pct_change):
	if (pct_change > 10.0):
		gain_loss_str = f'+{pct_change:5.02f}%'
	elif (pct_change > 0):
		gain_loss_str = f' +{pct_change:4.02f}%'
	else:
		gain_loss_str = f'{pct_change:6.02f}%'

	return gain_loss_str

def process_symbol(df, s):
	first_row = df.iloc[0]
	last_row = df.iloc[-1]
	o = first_row['Open']
	c = last_row['Close']
	pct_change = ((c/o)-1)*100.0

	gain_loss_str = format_gain_loss_1(pct_change)
#	gain_loss_str = format_gain_loss_2(pct_change)
	print(f'{g_year} {s:<5} {o:>9} -> {c:>9} = {gain_loss_str}')
	save_year_open(s, o)
#	save_daily_close(s, c)

def process_pickle(pickle_filename, symbols_list):
	ticker = pd.read_pickle(pickle_filename)
	for s in symbols_list:
		df = ticker[s].round(decimals=2)
		process_symbol(df, s)

def download_pickle(table_name, symbols_list):
	pickle_filename = f'{table_name}.1d.pickle'
	yfdata = yf.download(symbols_list, start=f'{g_year}-01-01', end=f'{g_year}-12-31', interval='1d', group_by='ticker', progress=False)
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
	parser = ArgumentParser()
	parser.add_argument('--year', '-y', type=int, required=True)
	args = parser.parse_args()
	g_year = args.year

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)

#	Why can't these be combined?
	index_list = ['^DJI', '^GSPC', '^IXIC', '^RUT']
	process_indices(index_list)

	index_list = ['^VIX']
	process_indices(index_list)