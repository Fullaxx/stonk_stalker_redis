#!/usr/bin/env python3

import os
import sys
import zmq
import json
import pytz
import redis
import signal
import datetime
#import traceback
#from pprint import pprint

import time
usleep = lambda x: time.sleep(x/1000000.0)

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

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

def dashboard_save(key, val):
	if val is None:
		eprint(f'{key} has NULL vlaue - NOT SETTING!')
		return

	result = g_rc.set(key, val)
	if result:
		print(f'SET {key:<40} {val}', flush=True)
	else:
		eprint(f'SET {key:<40} FAILED!')

def analyze_time(rmt, etzn):
	exchange_zone = pytz.timezone(etzn)
	rmt_dt = datetime.datetime.fromtimestamp(rmt, tz=exchange_zone)
	rmt_z = rmt_dt.astimezone(pytz.UTC)
	now_z = datetime.datetime.now(pytz.UTC)
	rmt_zstamp = int(rmt_z.timestamp())
	now_zstamp = int(now_z.timestamp())
#	delta = now_dt - rmt_dt
#	seconds_ago = delta.total_seconds()
	seconds_ago = now_zstamp - rmt_zstamp
	print(f'{rmt_dt} was {seconds_ago} seconds ago')

def update_prevclose(src, symbol, pc, rmt, etzn):
	analyze_time(rmt, etzn)
	if symbol in g_non_stock_symbols_set:
		key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		dashboard_save(key, pc)

def update_price(src, symbol, cp, rmt, etzn):
	analyze_time(rmt, etzn)
	if symbol in g_non_stock_symbols_set:
		key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
		dashboard_save(key, cp)

def process_spark_item(src, item):
	rmt = None
	etzn = None
	this_symbol = item['symbol'].replace('-','/')
	resp_array = item['response']
	for r in resp_array:
		rmt = None
		if 'meta' in r:
			m = r['meta']
			if 'exchangeTimezoneName' in m:
				etzn = m['exchangeTimezoneName']
			if 'regularMarketTime' in m:
				rmt = m['regularMarketTime']
			if 'regularMarketPrice' in m:
				cp = m['regularMarketPrice']
				update_price(src, this_symbol, cp, rmt, etzn)

def process_quote_item(src, item):
	rmt = None
	etzn = None
	this_symbol = item['symbol'].replace('-','/')
	if 'exchangeTimezoneName' in item:
		etzn = item['exchangeTimezoneName']
	if 'regularMarketTime' in item:
		rmt = item['regularMarketTime']['raw']
	if 'regularMarketPrice' in item:
		cp = item['regularMarketPrice']['raw']
		update_price(src, this_symbol, cp, rmt, etzn)
	if 'regularMarketPreviousClose' in item:
		pc = item['regularMarketPreviousClose']['raw']
		update_prevclose(src, this_symbol, pc, rmt, etzn)

def process_body(body_str):
	quote = json.loads(body_str)
	if ('quoteResponse' in quote):
		resp = quote['quoteResponse']
		if (resp['error'] == None):
			quoteResponseResultArray = resp['result']
			for item in quoteResponseResultArray:
				process_quote_item('quote', item)
	if ('spark' in quote):
		spark = quote['spark']
		if (spark['error'] == None):
			sparkResultArray = spark['result']
			for item in sparkResultArray:
				process_spark_item('spark', item)

def process_resource(requested_symbol, resource_str):
	resource = json.loads(resource_str)
	if (resource['status'] == 200):
		process_body(resource['body'])

def acquire_environment():
	global g_debug_python

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	zmq_url = os.getenv('ZMQ_SOCK')
	if zmq_url is None: bailmsg('Set ZMQ_SOCK')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return redis_url,zmq_url

if __name__ == '__main__':
	redis_url,zmq_url = acquire_environment()

	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	crypto_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')
	g_non_stock_symbols_set = crypto_set.union(index_set).union(etf_set).union(future_set)

	ctx = zmq.Context()
	receiver = ctx.socket(zmq.PULL)
	receiver.bind(zmq_url)

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	while not g_shutdown:
		try:
			symbol_bin, resource_bin = receiver.recv_multipart(flags=zmq.NOBLOCK)
		except zmq.ZMQError as e:
			if (e.errno == zmq.EAGAIN):
				usleep(1000)
			else:
#				traceback.print_exc()
				bailmsg(e)
		else:
			symbol_str = symbol_bin.decode('utf-8')
			resource_str = resource_bin.decode('utf-8')
			process_resource(symbol_str, resource_str)
