#!/usr/bin/env python3
# pip3 install redis,pandas,pandas_ta,yfinance

import os
import sys
import csv
import json
import time
import redis
#import shutil
import pandas as pd
import pandas_ta as ta
import yfinance as yf

#from pprint import pprint
#from pytz import timezone
#from contextlib import suppress
from datetime import datetime,date
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

def publish_message(r, symbol, key):
#	Publish a message indicating an update to specified symbol
	channel = f'SOURCE:YFINANCE:UPDATED'
	message = f'{key}'
	r.publish(channel, message)

# GOOGL {"CLOSE": 188.4, "SMA_50": 173.31, "SMA_100": 167.63, "SMA_200": 167.3, "BB_LOWER": 157.21, "BB_MID": 178.3, "BB_UPPER": 199.4, "OPEN": 195.22, "HIGH": 197.0, "LOW": 187.74, "BB_PCT": 0.74, "1Y_LOW": 130.67, "1Y_HIGH": 201.42, "SYMBOL": "GOOGL", "DATE": "2024-12-19"}
# BRK/B {"CLOSE": 446.59, "SMA_50": 463.56, "SMA_100": 457.01, "SMA_200": 434.6, "BB_LOWER": 448.39, "BB_MID": 467.91, "BB_UPPER": 487.42, "OPEN": 457.06, "HIGH": 458.73, "LOW": 446.09, "BB_PCT": -0.05, "1Y_LOW": 353.63, "1Y_HIGH": 491.67, "SYMBOL": "BRK-B", "DATE": "2024-12-19"}
def publish_macro_dict(r, yf_symbol, macro):
	symbol = yf_symbol.replace('-','/')
	macro['SYMBOL'] = yf_symbol
#	Assume TZ=US/Eastern
	macro['DATE'] = f'{date.today()}'
	json_str = json.dumps(macro)
	print(symbol, json_str)
	key = f'YFINANCE:DAILYINDICATORS:STOCK:{symbol}'
	r.set(key, json_str)
	publish_message(r, symbol, key)

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
	macro['BB_MID'] = 0
	macro['BB_UPPER'] = 0
	macro['BB_PCT'] = 0
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
	macro['1Y_LOW'] = per_lo
	macro['1Y_HIGH'] = per_hi
	return macro

def gen_daily_csv(df, yf_symbol):
#	Drop the rows where at least one element is missing in the specified columns
	df = df.dropna(subset=['Open','High','Low','Close'])
	if df.empty: return None

#	Add Close%Change and Volume%Change columns
	df['C%'] = df['Close'].pct_change().apply(lambda x: x*100)
	df['V%'] = df['Volume'].pct_change().apply(lambda x: x*100)

	DailyStrategy = ta.Strategy(
		name = 'Daily Strategy',
		description = 'OBV, ROC, SMA50, SMA100, SMA200, EMA5, EMA10, EMA20, WILLR, RSI, MACD, STOCH, ADX, BB',
		ta = [
			{'kind': 'obv'},
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
			{'kind': 'stoch', 'k': 14},
			{'kind': 'adx', 'length': 14},
			{'kind': 'bbands', 'length': 20, 'std': 2}
		]
	)

	df.ta.cores = 0
	df.ta.strategy(DailyStrategy)
	df = rename_strategy_columns(df)
	df = df.round(decimals=2)
	csv_filename = f'{yf_symbol}.1d.csv'
	df.to_csv(csv_filename, index=True, sep=',', encoding='utf-8')
	return csv_filename

# Generate a dictionary of macro indicators
# the key is yf_symbol
# the value is a json object of data
def gen_daily_indicators(pickle_filename, yf_symbol_list, r):
	macro_dict = {}
	ticker = pd.read_pickle(pickle_filename)
	for yf_symbol in yf_symbol_list:
		df = ticker[yf_symbol].copy()
		csv_filename = gen_daily_csv(df, yf_symbol)
		if csv_filename is not None:
			macro = get_macro_indicators(csv_filename, None)
			if macro is not None:
				macro_dict[yf_symbol] = macro

	return macro_dict

def download_pickle(r, table_name, symbols_list):
	pickle_filename = f'{table_name}.1d.pickle'
	yfdata = yf.download(symbols_list, period='1y', interval='1d', group_by='ticker', progress=False)
	yfdata.to_pickle(pickle_filename)
	return pickle_filename

#	Loop through each table and do the following:
#	1) download a pickle
#	2) generate daily indicators of each symbol in the table
#	3) publish macro indicators for each symbol
def process_table(table_name, val):
	yf_symbols_list = []
	symbols_list = val.split(',')
	for s in symbols_list:
		yf_symbol = s.replace('/','-')
		yf_symbols_list.append(yf_symbol)

	print(f'{table_name:<10} {val}')

	pickle_filename = download_pickle(r, table_name, yf_symbols_list)
	macro_dict = gen_daily_indicators(pickle_filename, yf_symbols_list, r)
	for k,v in macro_dict.items():
		publish_macro_dict(r, k, v)

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
#	parser.add_argument('--table_name', '-t', type=str, required=True)
#	parser.add_argument('--symbol', '-s', type=str, required=True)
	parser.add_argument('--key', '-k', type=str, required=True)
	parser.add_argument('--dir', '-d', type=str, required=True)
	args = parser.parse_args()

	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)

	os.chdir(args.dir)

	key = args.key
	val = r.get(key)
	if val is None: bailmsg(f'{key} returned None!')

	table_name = key.split(':')[4]
	table_name_formatted = table_name.replace('/','-')
	process_table(table_name_formatted, val)
