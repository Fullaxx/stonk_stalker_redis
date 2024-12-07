#!/usr/bin/env python3
#
# https://pypi.org/project/websocket-client/
# https://websocket-client.readthedocs.io/en/latest/examples.html
# python3 -m pip install websocket-client wsaccel rel
#
# https://alpaca.markets/learn/streaming-market-data/
# https://docs.alpaca.markets/docs/real-time-stock-pricing-data

import os
import sys
import rel
import time
import pytz
import json
import redis
import _thread
import datetime
import websocket

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_rc = None
g_symbolset = None

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def handle_market_message_orig(ws, obj):
	symbol = obj['S']
	if os.getenv('SYMBOL') is not None:
		if (symbol != os.getenv('SYMBOL')): return
#	field = symbol.replace('/', '_')	#	Crypto Symbol Converted
	bar_time = obj['t']
	zulu_dt = datetime.datetime.strptime(bar_time, '%Y-%m-%dT%H:%M:%S%z')
	zstamp = zulu_dt.strftime('%s')
	eastern_dt = zulu_dt.astimezone(g_etz)
#	Stock Market datestamps should always be localized to US/eastern
	if (g_exchange ==  'STOCK'): date_str = eastern_dt.strftime('%Y%m%d')
	if (g_exchange == 'CRYPTO'): date_str = zulu_dt.strftime('%Y%m%d')

	print(zstamp, 'Z /', zulu_dt, '/', eastern_dt, '/', date_str, symbol, flush=True)

#	Make sure our bar is in proper JSON format
	bar_str = json.dumps(obj)

#	This should return 1 every time
	key = f'{g_exchange}:RAWBARS:HMAP_1MINBARS:{date_str}:{zstamp}'
	hupd = g_rc.hset(key, symbol, bar_str)

#	Publish a message indicating an update to specified symbol
	channel = f'{g_exchange}-RAWBARS-UPDATED'
	message = f'{symbol}:{date_str}:{zstamp}'
	g_rc.publish(channel, message)

	if g_debug_python:
		print(f'{key} {symbol} {bar_str}', flush=True)

def publish_message(symbol, key):
#	Publish a message indicating an update to specified symbol
	channel = f'SOURCE:ALPACA:UPDATED'
	message = f'{key}'
	g_rc.publish(channel, message)

def handle_market_message_dailybars(ws, obj):
	symbol = obj['S']
#	if g_debug_python: print(f'AlpacaDailyBars: {obj}', flush=True)
	if (g_rc is None) or (g_symbolset is None): return

	if ((symbol in g_symbolset) or (g_exchange == 'CRYPTO')):
		if g_debug_python: print(f'AlpacaDailyBars: {obj}', flush=True)
		key = f'ALPACA:DAILYBARS:{symbol}'
		val = json.dumps(obj)
		g_rc.set(key, val)
		publish_message(symbol, key)

def handle_market_message_updatedbars(ws, obj):
	symbol = obj['S']
#	if g_debug_python: print(f'AlpacaUpdatedBars: {obj}', flush=True)
	if (g_rc is None) or (g_symbolset is None): return

	if ((symbol in g_symbolset) or (g_exchange == 'CRYPTO')):
		if g_debug_python: print(f'UpdatedBars: {symbol} @ {obj}', flush=True)
		key = f'ALPACA:1MINBARS:{symbol}'
		val = json.dumps(obj)
		g_rc.set(key, val)
		publish_message(symbol, key)

def handle_market_message_bars(ws, obj):
	symbol = obj['S']
#	if g_debug_python: print(f'AlpacaBars: {symbol} @ {obj}', flush=True)
	if (g_rc is None) or (g_symbolset is None): return

	if ((symbol in g_symbolset) or (g_exchange == 'CRYPTO')):
		if g_debug_python: print(f'AlpacaBars: {symbol} @ {obj}', flush=True)
		key = f'ALPACA:1MINBARS:{symbol}'
		val = json.dumps(obj)
		g_rc.set(key, val)
		publish_message(symbol, key)

def handle_market_message_trade(ws, obj):
	symbol = obj['S']
	price = obj['p']
	print(f'AlpacaTrade: {symbol} @ {price}', flush=True)
#	if g_rc is not None:
#		key = f'ALPACA:TRADE:{symbol}'
#		g_rc.set(key, price)

def handle_market_message_quote(ws, obj):
	symbol = obj['S']
	bid_price = obj['bp']
	ask_price = obj['ap']
	print(f'AlpacaQuote: {symbol} @ {bid_price} / {ask_price}', flush=True)

def handle_market_message_orderbook(ws, obj):
	if g_debug_python: print('AlpacaOrderBook', flush=True)

def handle_market_message(ws, obj):
	msg_type = obj['T']
#	symbol = obj['S']
	if   (msg_type == 'o'): handle_market_message_orderbook(ws, obj)
	elif (msg_type == 'q'): handle_market_message_quote(ws, obj)
	elif (msg_type == 't'): handle_market_message_trade(ws, obj)
	elif (msg_type == 'b'): handle_market_message_bars(ws, obj)
	elif (msg_type == 'd'): handle_market_message_dailybars(ws, obj)
	elif (msg_type == 'u'): handle_market_message_updatedbars(ws, obj)
	else: print(obj, flush=True)

def create_alpaca_wss_sub_msg():
	subact = {'action':'subscribe'}
#	list_of_symbols = args.symbols.split(',')
#	if (g_exchange ==  'STOCK'): list_of_symbols = ('AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN', 'NVDA', 'AVGO', 'MU', 'PLTR', 'SMCI', 'VRT')
#	if (g_exchange == 'CRYPTO'): list_of_symbols = ('BTC/USD', 'ETH/USD', 'LTC/USD', 'DOGE/USD')
#	json_list_of_symbols = json.dumps(list_of_symbols)
#	subact['orderbooks']  = list_of_symbols
#	subact['trades']      = list_of_symbols
#	subact['quotes']      = list_of_symbols
	subact['bars']        = list('*')
	subact['updatedBars'] = list('*')
	subact['dailyBars']   = list('*')
	sub_str = json.dumps(subact)
	return sub_str

def handle_server_success(ws, obj):
	print(obj, flush=True)
	if (obj['msg'] == 'connected'):
		ws.send('{"action":"auth","key":"%s","secret":"%s"}' % (g_apikey, g_secret))
	if (obj['msg'] == 'authenticated'):
		sub_str = create_alpaca_wss_sub_msg()
		ws.send(sub_str)
#		ws.send('{"action":"subscribe","trades":["BTC/USD","ETH/USD"],"quotes":["BTC/USD","bars":["*"],"updatedBars":["*"],"dailyBars":["*"]}')
#		ws.send('{"action":"subscribe","trades":["BTC/USD","ETH/USD"],"quotes":["BTC/USD","ETH/USD"],"orderbooks":["BTC/USD","ETH/USD"]}')

# {'T': 'error', 'code': 406, 'msg': 'connection limit exceeded'}
# if (obj['code'] == 406)
# if (obj['msg'] == 'connection limit exceeded')
def handle_server_errors(ws, obj):
	print(obj, flush=True)

def handle_server_subscriptions(ws, obj):
	print(obj, flush=True)

def on_message(ws, message):
	messages = json.loads(message)
	for obj in messages:
		if (obj['T'] == 'error'):
			handle_server_errors(ws, obj)
		elif (obj['T'] == 'success'):
			handle_server_success(ws, obj)
		elif (obj['T'] == 'subscriptions'):
			handle_server_subscriptions(ws, obj)
		else:
#			handle_market_message_orig(ws, obj)
			handle_market_message(ws, obj)

def on_error(ws, error):
	print('WSERR:', error, flush=True)

def on_close(ws, close_status_code, close_msg):
	print('Connection: Closed', flush=True)

def on_open(ws):
	print('Connection: Opened', flush=True)

def acquire_environment():
	global g_etz, g_apikey, g_secret, g_exchange, g_debug_python

	g_etz = pytz.timezone('US/Eastern')

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')
#	if redis_url is None: print('REDIS_URL is NULL (Not connecting)', flush=True)

	g_apikey = os.getenv('ALPACA_APIKEY')
	if g_apikey is None: bailmsg('Set ALPACA_APIKEY')
	g_secret = os.getenv('ALPACA_SECRET')
	if g_secret is None: bailmsg('Set ALPACA_SECRET')
	g_exchange = os.getenv('EXCHANGE')
	if g_exchange is None: bailmsg('Set EXCHANGE')

	if (g_exchange == 'CRYPTO'): wssurl = 'wss://stream.data.alpaca.markets/v1beta3/crypto/us'
	elif (g_exchange == 'STOCK'): wssurl = 'wss://stream.data.alpaca.markets/v2/iex'
	else: bailmsg('EXCHANGE == <CRYPTO|STOCK>')

	g_debug_python = False
	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return wssurl,redis_url

if __name__ == '__main__':
	wssurl,redis_url = acquire_environment()

	if redis_url is not None:
		g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
		g_symbolset = g_rc.smembers(f'SSCFG:SYMBOLSET')

	wss_dbg_trace = False
	websocket.enableTrace(wss_dbg_trace)
	ws = websocket.WebSocketApp(wssurl,
		on_open=on_open,
		on_message=on_message,
		on_error=on_error,
		on_close=on_close)

#	Set dispatcher to automatic reconnection, 1 second reconnect delay if connection closed unexpectedly
	ws.run_forever(dispatcher=rel, reconnect=1)
	rel.signal(2, rel.abort)  # Keyboard Interrupt
	rel.dispatch()
