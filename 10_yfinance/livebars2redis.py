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
g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,is_market_open

g_debug_python = False
g_debug_open_market = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

#def save_year_open(s, o):
#	g_rc.set(f'DASHBOARD:DATA:YEAROPEN:{s}', o)

def save_currentprice(s, cp, z):
	symbol = s.replace('-','/')
	d = datetime.datetime.fromtimestamp(z, tz=g_tz_et)
	print(f'{symbol:<9} ${cp:<9} @ {d}')
	g_rc.set(f'DASHBOARD:DATA:CURRENTPRICE:{symbol}', cp)

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
#def format_gain_loss_1(pct_change):
#	if (pct_change > 10.0):
#		gain_loss_str = f'+{pct_change:5.02f}%'
#	elif (pct_change > 0):
#		gain_loss_str = f' +{pct_change:4.02f}%'
#	else:
#		gain_loss_str = f'{pct_change:6.02f}%'
#
#	return gain_loss_str

# After the trading session is closed, grab the daily bars
# Save the daily close as the current price
# Save the 1st open as the year open value (NOT ANYMORE)
def process_daily_post(df, s):
	first_row = df.iloc[0]
	last_row = df.iloc[-1]
	o = first_row['Open']
	c = last_row['Close']
	pct_change = ((c/o)-1)*100.0

#	gain_loss_str = format_gain_loss_1(pct_change)
#	gain_loss_str = format_gain_loss_2(pct_change)
#	print(f'{g_year} {s:<5} {o:>9} -> {c:>9} = {gain_loss_str}')
#	save_year_open(s, o)

	now_dt = datetime.datetime.now(g_tz_utc)
	z = now_dt.timestamp()
	save_currentprice(s, c, int(z))

# Analyze the 1m bars during the live trading session
# Grab the last close of the last bar and save it as the current price
def process_bars(df, s):
	z = df.index[-1].strftime('%s')
	last_row = df.iloc[-1]
	c = last_row['Close']
	save_currentprice(s, c, int(z))

def process_funds(symbols_list):
	yf_symbols_list = []
	for s in symbols_list:
		yf_symbol = s.replace('/','-')
		yf_symbols_list.append(yf_symbol)

#	if g_market_is_open:
#		yfresp = yf.download(yf_symbols_list, period='1d', interval='1m', group_by='ticker', progress=False, prepost=False)
#	else:
#		yfresp = yf.download(yf_symbols_list, start=f'{g_year}-01-01', end=f'{g_year}-12-31', interval='1d', group_by='ticker', progress=False, prepost=False)

	yfresp = yf.download(yf_symbols_list, period='1d', interval='1m', group_by='ticker', progress=False, prepost=False)
	for s in yf_symbols_list:
		if s not in yfresp:
			eprint(f'{s} NOT FOUND IN yf.download({symbols_list})!')
			continue
		df = yfresp[s].round(decimals=2).dropna()
		if (len(df.index) == 0):
			eprint(f'yf.download({s}) produced an empty data series!')
			continue

		process_bars(df, s)

def acquire_environment():
	global g_debug_python, g_debug_open_market

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	debug_env_var = os.getenv('DEBUG_OPEN_MARKET')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_open_market = True
		if (debug_env_var == 'on'): g_debug_open_market = True
		if (debug_env_var == 'ON'): g_debug_open_market = True

	return redis_url

if __name__ == '__main__':
	g_today = datetime.datetime.today()
#	if ((g_today.month == 1) and (g_today.day == 1)): bailmsg('Skipping Today (New Years Day)!')
	g_year = g_today.year
	if ((g_today.month == 1) and (g_today.day == 1)): g_year = g_year - 1

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	if g_debug_open_market:
		g_market_is_open = True
	else:
		g_market_is_open = is_market_open(g_rc, 0.1)

#	stock_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:STOCKS')
	crypto_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')

	if g_market_is_open:
		symbols_set = crypto_set.union(index_set).union(etf_set).union(future_set)
	else:
		symbols_set = crypto_set

	process_funds(symbols_set)
