#!/usr/bin/env python3
# pip3 install redis,pandas,yfinance

import os
import sys
import redis
import datetime

import pandas as pd
import yfinance as yf

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,is_market_open

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

#2024 ^DJI   37566.22 ->  42573.73 = +13.33%
#2024 ^GSPC    4745.2 ->   5906.94 = -24.24%
#2024 ^IXIC   14873.7 ->  19486.79 = - 7.77%
#2024 ^RUT    2012.75 ->   2227.78 = + 9.09%
#def format_gain_loss_2(pct_change):
#	gain_loss = round(pct_change, 2)
#	gain_loss_str = ''
#	if (pct_change > 0):
#		gain_loss_str += '+'
#		gain_loss = pct_change
#	if (pct_change < 0):
#		gain_loss_str += '-'
#		gain_loss = abs(pct_change)
#
#	gain_loss_str += f'{gain_loss:5.02f}%'
#	return gain_loss_str

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

# After the trading session is closed for the year, grab the daily bars
# Save the last close as the year close value
def process_last_year(df, s):
	first_row = df.iloc[0]
	last_row = df.iloc[-1]
	o = first_row['Open']
	c = last_row['Close']
	pct_change = ((c/o)-1)*100.0

	gain_loss_str = format_gain_loss_1(pct_change)
#	gain_loss_str = format_gain_loss_2(pct_change)
	print(f'{g_year} {s:<5} {o:>9} -> {c:>9} = {gain_loss_str}')
	g_rc.set(f'DASHBOARD:DATA:{g_year}:YEARCLOSE:{s}', c)

def process_indices(symbols_list):
	yfresp = yf.download(symbols_list, start=f'{g_year}-01-01', end=f'{g_year}-12-31', interval='1d', group_by='ticker', progress=False, prepost=False)

	for s in symbols_list:
		if s not in yfresp:
			eprint(f'{s} NOT FOUND IN yf.download({symbols_list})!')
			continue
		df = yfresp[s].round(decimals=2).dropna()
		if (len(df.index) == 0):
			eprint(f'yf.download({s}) produced an empty data series!')
			continue

		process_last_year(df, s)

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
	g_today = datetime.datetime.today()
#	if ((g_today.month == 1) and (g_today.day == 1)): RUN ME ON NEW YEARS DAY
	g_year = g_today.year - 1
	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)

	searchpattern = f'DASHBOARD:TABLES:*'
	all_tables_list = sorted(g_rc.scan_iter(searchpattern))
	for key in all_tables_list:
		val = g_rc.get(key)
		if val is None: continue
		table_name = key.split(':')[-1]
		table_name_formatted = table_name.replace('/','-')
		print(key, table_name_formatted)
		#process_table(table_name_formatted, val)


#	REWORK THIS TO GRAB EVERYTHING??

#	index_list = ['^DJI', '^GSPC', '^IXIC', '^RUT', '^VIX']
#	process_indices(index_list)
#
#	index_list = ['NVDL', 'QDTE', 'SPY', 'QQQ', 'VGT']
#	process_indices(index_list)
