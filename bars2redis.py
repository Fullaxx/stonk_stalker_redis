#!/usr/bin/env python3
# pip3 install redis yfinance

import os
import sys
import json
import time
import redis
import signal
import shutil
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from pytz import timezone
from datetime import datetime

from contextlib import suppress
#from pprint import pprint

usleep = lambda x: time.sleep(x/1000000.0)

g_datadir = '/tmp/blackhole'
g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def bailmsg(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	exit(1)

def push_macro_indicators_to_redis(r, symb):
	pass

def get_macro_indicators(filename, before_this_date):
	if not os.path.exists(filename): return None
	ignoring_after_sec = 0
	if before_this_date is not None:
		ignoring_after_str = datetime.fromisoformat(before_this_date).strftime('%s')
		ignoring_after_sec = int(ignoring_after_str)

	macro = {}
	per_lo = 999999999
	per_hi = -999999999
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
			row_lo = float(row['Low'])
			row_hi = float(row['High'])
			if (row_lo < per_lo): per_lo = row_lo
			if (row_hi > per_hi): per_hi = row_hi
			row_sma50 = row.get('SMA_50')
			if row_sma50: macro['SMA_50'] = float(row_sma50)
			row_sma100 = row.get('SMA_100')
			if row_sma100: macro['SMA_100'] = float(row_sma100)
			row_sma200 = row.get('SMA_200')
			if row_sma200: macro['SMA_200'] = float(row_sma200)
			row_bb_lower = row.get('BBL_20_2.0')
			if row_bb_lower: macro['BB_LOWER'] = float(row_bb_lower)
			row_bb_upper = row.get('BBU_20_2.0')
			if row_bb_upper: macro['BB_UPPER'] = float(row_bb_upper)
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
	df = df.round(decimals=2)
	df.to_csv(csv_filename, index=True, sep=',', encoding='utf-8')

def gen_daily_csvs(pickle_filename, symb_list):
	ticker = pd.read_pickle(pickle_filename)
	for symb in symb_list:
		df = ticker[symb].copy()
		csv_filename = f'{g_datadir}/{symb}.1d.csv'
		gen_daily_csv(df, csv_filename)
		macro = get_macro_indicators(csv_filename, None)
		push_macro_indicators_to_redis(symb)

def download_daily_bars(r, symb_list):
	with suppress(FileExistsError): os.mkdir(g_datadir)
	data = yf.download(symb_list, period='1y', interval='1d', group_by='ticker', progress=False)
	data.to_pickle(f'{g_datadir}/daily.pickle')
	gen_daily_csvs(f'{g_datadir}/daily.pickle', symb_list)
#	shutil.rmtree(g_datadir)

def every_min(r, now, symb_list):
	mstamp = now.strftime('%H%M')
	if (mstamp == '2301'):
		download_daily_bars(r, symb_list)

if __name__ == '__main__':
	redis_url = os.getenv('REDISURL')
	if redis_url is None: bailmsg('Set REDISURL')
	symbols_str = os.getenv('SYMBOLS')
	if symbols_str is None: bailmsg('Set SYMBOLS')

	r = redis.from_url(redis_url)
	connected = r.ping()
	if not connected: exit(1)
	print('Redis Connected:', connected)

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	last_trigger = 0
	tz = timezone('US/Eastern')
	symb_list = symbols_str.split(' ')

#	download_daily_bars(r, symb_list)
#	exit(0)

	while not g_shutdown:
		now = datetime.now(tz)
		now_sec = int(now.strftime('%s'))
		if (now_sec % 60 == 0) and (now_sec > last_trigger):
			update_symbols(r, now, symb_list)
			last_trigger = now_sec
		usleep(1000)
