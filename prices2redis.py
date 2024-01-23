#!/usr/bin/env python3
# pip3 install redis yfinance

import os
import sys
import json
import time
import redis
import signal
from pytz import timezone
from datetime import datetime
import yfinance as yf
#from pprint import pprint

usleep = lambda x: time.sleep(x/1000000.0)

g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def bailmsg(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	exit(1)

def update_symbols(r, symbols_str):
	cp_obj = {}
	symb_list = symbols_str.split(' ')
	resp = yf.Tickers(symbols_str)
	for symb in symb_list:
		symb_info = resp.tickers[symb].info
#		pprint(symb_info)
		p = symb_info['currentPrice']
		cp_obj[symb] = round(p,2)
	cp_str = json.dumps(cp_obj)
	r.set('MARKET:PRICES', cp_str)

# This function is pretty generic and could use some better logic to determine an active trading session
def trading_is_active(now):
	active = False
	day = now.strftime('%a')
	hour = int(now.strftime('%H'))
	if (day == 'Sun'): return False
	if (day == 'Sat'): return False
	if ((hour >= 9) and (hour <= 16)):
		active = True
	return active

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
	while not g_shutdown:
		now = datetime.now(tz)
		now_sec = int(now.strftime('%s'))
		if (now_sec % 5 == 0) and (now_sec > last_trigger):
			if trading_is_active(now):
				update_symbols(r, symbols_str)
				last_trigger = now_sec
		usleep(1000)
