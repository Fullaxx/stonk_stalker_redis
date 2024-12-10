#!/usr/bin/env python3

import os
import sys
import time

sys.path.append('.')
sys.path.append('/app')
from ss_cfg import read_ss_config

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

if __name__ == '__main__':
	ri_str = os.getenv('YFINANCE_REQUEST_INTERVAL')
	request_interval = 20 if ri_str is None else int(ri_str)

#	Acquite the list of symbols from the config
	symbols_list = []
	ss_config = read_ss_config()
	for k,v in ss_config.items():
		if k.startswith('TABLE_'):
			symbols_str = v['SYMBOLS']
			symbols_list += symbols_str.split(',')

#	When this loop is done, it will exit 0
#	Current Design: supervisord will restart it automatically
	for symbol in symbols_list:
		os.system(f'/app/yfinfo2redis.py -s {symbol}')
		time.sleep(request_interval)
