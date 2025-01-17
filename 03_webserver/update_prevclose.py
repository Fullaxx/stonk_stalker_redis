#!/usr/bin/env python3
# pip3 install redis

import os
import sys
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
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)

#	Grab the CURRENTPRICE value and set PREVIOUSCLOSE to it
	searchpattern = f'DASHBOARD:DATA:CURRENTPRICE:*'
	for key in sorted(g_rc.scan_iter(searchpattern)):
		cp = g_rc.get(key)
		if cp is None: continue
		symbol = key.split(':')[3]
		prev_close_key = f'DASHBOARD:DATA:PREVIOUSCLOSE:{symbol}'
		print(f'Setting {prev_close_key} to ${cp}: ', flush=True)
		g_rc.set(prev_close_key, cp)
