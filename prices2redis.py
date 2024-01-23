#!/usr/bin/env python3
# pip3 install redis yfinance

import os
import sys
import json
import time
import redis
import yfinance as yf

def bailmsg(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	exit(1)

def update_symbols(r, symbols_str):
	cp_obj = {}
	symb_list = symbols_str.split(' ')
	resp = yf.Tickers(symbols_str)
	for symb in symb_list:
		symb_info = resp.tickers[symb].info
		p = symb_info['currentPrice']
		cp_obj[symb] = round(p,2)
	cp_str = json.dumps(cp_obj)
	r.set('MARKET:PRICES', cp_str)

if __name__ == '__main__':
	redis_url = os.getenv('REDISURL')
	if redis_url is None: bailmsg('Set REDISURL')
	symbols_str = os.getenv('SYMBOLS')
	if symbols_str is None: bailmsg('Set SYMBOLS')

	r = redis.from_url(redis_url)
	while True:
		update_symbols(r, symbols_str)
		time.sleep(30)
