#!/usr/bin/env python3

import os
import sys
import time

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

if __name__ == '__main__':
	ticker_tables = os.getenv('TICKER_TABLES')
	if ticker_tables is None: bailmsg('Set TICKER_TABLES')

	ri_str = os.getenv('REQUEST_INTERVAL')
	request_interval = 30 if ri_str is None else int(ri_str)

	symb_list = []
	tables_list = ticker_tables.split(';')
	for tbl in tables_list:
		symbols = tbl.split('=')[1]
		symb_list += symbols.split(',')

#	When this loop is done, it will exit 0
#	Current Design: supervisord will restart it automatically
	for symb in symb_list:
		os.system(f'/app/yfTickerInfo2Redis.py -s {symb}')
		time.sleep(request_interval)
