#!/usr/bin/env python3

import os
import sys
import zmq
import json
import time
import redis
import signal
#import traceback
#from pprint import pprint

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

usleep = lambda x: time.sleep(x/1000000.0)

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

def dashboard_save(symbol, key, val):
	if val is None:
		eprint(f'{key} has NULL vlaue - NOT SETTING!')
		return

	result = g_rc.set(key, val)
	if result:
		print(f'SET {key:<20} {val}', flush=True)
	else:
		eprint(f'SET {key:<20} FAILED!')

def update_prevclose(src, symbol, pc):
	if symbol in g_non_stock_symbols_set:
		key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		dashboard_save(symbol, key, pc)
#		print(f'{src}: {s} @ ${pc} prev')

def update_price(src, symbol, cp):
	if symbol in g_non_stock_symbols_set:
		key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
		dashboard_save(symbol, key, cp)
#		print(f'{src}: {s} @ ${cp}')

def process_spark(resultarray):
	src = 'spark'
#	pprint(resultarray)
	for item in resultarray:
		this_symbol = item['symbol']
		resp_array = item['response']
		for r in resp_array:
			if 'meta' in r:
				m = r['meta']
				if 'regularMarketPrice' in m:
					cp = m['regularMarketPrice']
					update_price(src, this_symbol, cp)

def process_quote_response(resultarray):
	src = 'quote'
#	pprint(resultarray)
	for item in resultarray:
		this_symbol = item['symbol']
		if 'regularMarketPrice' in item:
			cp = item['regularMarketPrice']['raw']
			update_price(src, this_symbol, cp)
		if 'regularMarketPreviousClose' in item:
			pc = item['regularMarketPreviousClose']['raw']
			update_prevclose(src, this_symbol, pc)

def process_body(body_str):
	quote = json.loads(body_str)
#	pprint(quote)
	if ('quoteResponse' in quote):
		resp = quote['quoteResponse']
		if (resp['error'] == None):
			quoteResponseResultArray = resp['result']
			process_quote_response(quoteResponseResultArray)
	if ('spark' in quote):
		spark = quote['spark']
		if (spark['error'] == None):
			sparkResultArray = spark['result']
			process_spark(sparkResultArray)

def process_resource(requested_symbol, resource_str):
	resource = json.loads(resource_str)
#	pprint(resource)
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
	index_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:ETF')
	future_set = g_rc.smembers('DASHBOARD:SYMBOLS_SET:FUTURE')
	g_non_stock_symbols_set = index_set.union(etf_set).union(future_set)

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
