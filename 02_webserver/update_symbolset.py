#!/usr/bin/env python3
# pip3 install redis,yfinance

import os
import sys
import json
import time
import redis

sys.path.append('.')
sys.path.append('/app')
from ss_cfg import read_ss_config
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def save_symbols(r, symbols_str):
	key = f'SSCFG:SYMBOLSET'
	symbols_list = symbols_str.split(',')
	num_updated = r.sadd(key, *symbols_list)
	print(f'{key} {symbols_list}: {num_updated}', flush=True)

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
	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)

#	Delete the set and re-create??
#	key = f'SSCFG:SYMBOLSET'
#	r.delete(key)

	ss_config = read_ss_config()
	for k,v in ss_config.items():
		if k.startswith('TABLE_'):
			save_symbols(r, v['SYMBOLS'])

#	r.set('SSCFG:SYMBOLSET:READY') EX 15

	time.sleep(2)
#	Sleep for a bit so supervisord knows all is well
