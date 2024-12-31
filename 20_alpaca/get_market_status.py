#!/usr/bin/env python3

import os
import sys
#import time
#import pytz
import json
import redis
#import datetime

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def connect_to_redis(redis_url):
	if g_debug_python: print(f'REDIS_URL: {redis_url}', flush=True)
	r = redis.Redis.from_url(redis_url, decode_responses=True)
	connected = r.ping()
	if not connected: bailmsg('r.ping() failed!')
	print(f'Connected to redis @ {redis_url}', flush=True)
	return r

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
	r = connect_to_redis(redis_url)

	market_clock = r.get('MARKET:CLOCK')
	print(market_clock)

	market_status = r.get('MARKET:STATUS')
	print(market_status)
