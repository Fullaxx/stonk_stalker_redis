#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import time
import redis

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def write_to_file(text, filename):
	with open(filename, 'w') as f:
		f.write(text)
		f.close()

def acquire_environment():
	global g_debug_python

	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)

	if os.getenv('REDIS_URL') is None: bailmsg('Set REDIS_URL')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

if __name__ == '__main__':
	acquire_environment()
	r = connect_to_redis(os.getenv('REDIS_URL'), True, False, g_debug_python)
	symb_set = r.smembers('SSCFG:SYMBOLSET')
	marketdb = {}
	for symbol in symb_set:
		key = f'YFINANCE:INFO:{symbol}'
		info_str = r.get(key)
		info = json.loads(info_str)
		marketdb[symbol] = info

	market_str = json.dumps(marketdb)
	filename = f'yf_info.json'
	print(f'Writing {filename} ...')
	write_to_file(market_str, filename)
	time.sleep(59)
