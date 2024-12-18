#!/usr/bin/env python3
# pip3 install redis,yfinance

import os
import sys
import csv
import json
import redis
import shutil
import pandas as pd
import pandas_ta as ta
import yfinance as yf

from pprint import pprint
from pytz import timezone
from datetime import datetime
from contextlib import suppress
#from argparse import ArgumentParser

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_datadir = '/data'
g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def publish_message(r, symbol, key):
#	Publish a message indicating an update to specified symbol
	channel = f'SOURCE:YFINANCE:INDICATORS:UPDATED'
	message = f'{key}'
	r.publish(channel, message)

def publich_macro_dict(symbol, macro):
	daily_indicators = {symbol: macro}
	pprint(daily_indicators)

def rename_strategy_columns(df):
	new_STOCH_column_names = {'STOCHk_14_3_3':'STOCHk_14','STOCHd_14_3_3':'STOCHd_14'}
	new_BB_column_names = {'BBL_20_2.0':'BBl','BBM_20_2.0':'BBm','BBU_20_2.0':'BBu','BBB_20_2.0':'BBw','BBP_20_2.0':'BBp'}
	new_NACD_column_names = {'MACD_12_26_9':'MACD','MACDh_12_26_9':'MACDh','MACDs_12_26_9':'MACDs'}
	new_column_names = {**new_STOCH_column_names, **new_BB_column_names, **new_NACD_column_names}
	return df.rename(columns=new_column_names)

def get_macro_indicators(filename, before_this_date):
	if not os.path.exists(filename): return None

	ignoring_after_sec = 0
	if before_this_date is not None:
		ignoring_after_str = datetime.fromisoformat(before_this_date).strftime('%s')
		ignoring_after_sec = int(ignoring_after_str)

	macro = {}
	per_lo = 999999999
	per_hi = -999999999
	macro['CLOSE'] = 0
	macro['SMA_50'] = 0
	macro['SMA_100'] = 0
	macro['SMA_200'] = 0
	macro['BB_LOWER'] = 0
	macro['BB_UPPER'] = 0
	with open(filename) as f:
		reader = csv.DictReader(f, delimiter=',', quotechar='"')
		for row in reader:
			row_time_str = datetime.fromisoformat(row['Date']).strftime('%s')
			if ((ignoring_after_sec > 0) and (int(row_time_str) >= ignoring_after_sec)): break
			row_open = float(row['Open'])
			macro['OPEN'] = row_open
			row_hi = float(row['High'])
			macro['HIGH'] = row_hi
			row_lo = float(row['Low'])
			macro['LOW'] = row_lo
			row_close = float(row['Close'])
			macro['CLOSE'] = row_close
			if (row_lo < per_lo): per_lo = row_lo
			if (row_hi > per_hi): per_hi = row_hi
			row_sma50 = row.get('SMA_50')
			if row_sma50: macro['SMA_50'] = float(row_sma50)
			row_sma100 = row.get('SMA_100')
			if row_sma100: macro['SMA_100'] = float(row_sma100)
			row_sma200 = row.get('SMA_200')
			if row_sma200: macro['SMA_200'] = float(row_sma200)
			row_bb_lower = row.get('BBl')
			if row_bb_lower: macro['BB_LOWER'] = float(row_bb_lower)
			row_bb_mid = row.get('BBm')
			if row_bb_mid: macro['BB_MID'] = float(row_bb_mid)
			row_bb_upper = row.get('BBu')
			if row_bb_upper: macro['BB_UPPER'] = float(row_bb_upper)
			row_bb_pct = row.get('BBp')
			if row_bb_pct: macro['BB_PCT'] = float(row_bb_pct)
	macro['PERIOD_LOW'] = per_lo
	macro['PERIOD_HIGH'] = per_hi
	return macro

def gen_daily_csv(df, csv_filename):
#	Drop the rows where at least one element is missing in the specified columns
	df = df.dropna(subset=['Open','High','Low','Close'])

#	Add Close%Change and Volume%Change columns
	df['C%'] = df['Close'].pct_change().apply(lambda x: x*100)
	df['V%'] = df['Volume'].pct_change().apply(lambda x: x*100)

	DailyStrategy = ta.Strategy(
		name = 'Daily Strategy',
		description = 'ROC, SMA50, SMA100, SMA200, EMA5, EMA10, EMA20, WILLR, RSI, MACD, ADX, BB',
		ta = [
			{'kind': 'roc', 'length': 1},
			{'kind': 'sma', 'length': 50},
			{'kind': 'sma', 'length': 100},
			{'kind': 'sma', 'length': 200},
			{'kind': 'ema', 'length': 5},
			{'kind': 'ema', 'length': 10},
			{'kind': 'ema', 'length': 20},
			{'kind': 'willr'},
			{'kind': 'rsi'},
			{'kind': 'macd', 'fast': 12, 'slow': 26},
			{'kind': 'adx', 'length': 14},
			{'kind': 'bbands', 'length': 20, 'std': 2}
		]
	)

	df.ta.cores = 0
	df.ta.strategy(DailyStrategy)
	df = rename_strategy_columns(df)
	df = df.round(decimals=2)
	df.to_csv(csv_filename, index=True, sep=',', encoding='utf-8')

def gen_daily_indicators(pickle_filename, symb_list, r):
	ticker = pd.read_pickle(pickle_filename)
#	daily_macro_list = []
	for symbol in symb_list:
		df = ticker[symbol].copy()
		csv_filename = f'{g_datadir}/{symbol}.1d.csv'
		gen_daily_csv(df, csv_filename)
		macro = get_macro_indicators(csv_filename, None)
		publich_macro_dict(symbol, macro)
#		daily_indicators = {symb: macro}
#		daily_macro_list.append(daily_indicators)
#	pprint(daily_macro_list)
#	daily_indicators_str = json.dumps(daily_macro_list)
#	print(daily_indicators_str)
#	r.set('MARKET:DAILYINDICATORS', daily_indicators_str)

def download_pickle(r, table_name, symb_list):
	pickle_filename = f'{g_datadir}/{table_name}.1d.pickle'
	yfdata = yf.download(symb_list, period='1y', interval='1d', group_by='ticker', progress=False)
	yfdata.to_pickle(pickle_filename)
	return pickle_filename

def acquire_environment():
	global g_debug_python

	redis_url = os.getenv('REDIS_URL')
#	if redis_url is None: bailmsg('Set REDIS_URL')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return redis_url

if __name__ == '__main__':
#	parser = ArgumentParser()
#	parser.add_argument('--symbol', '-s', type=str, required=True)
#	args = parser.parse_args()

	r = None
	redis_url = acquire_environment()
	if redis_url is not None:
		r = connect_to_redis(redis_url, True, False, g_debug_python)

	symb_list = []
	for s in ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'ORCL', 'AMZN', 'BRK/B']:
		yf_symbol = s.replace('/','-')
		symb_list.append(yf_symbol)

	with suppress(FileExistsError): os.mkdir(g_datadir)
	pickle_filename = download_pickle(r, 'table_name', symb_list)
	gen_daily_indicators(pickle_filename, symb_list, r)
#	shutil.rmtree(g_datadir)
