#!/usr/bin/env python3
# https://redis-py.readthedocs.io/en/stable/advanced_features.html
# https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html
# https://redis-py.readthedocs.io/en/v4.3.1/examples/asyncio_examples.html
# https://aioredis.readthedocs.io/en/v1.3.0/mpsc.html
# https://medium.com/@imamramadhanns/working-with-redis-keyspace-notifications-x-python-c5c6847368a
# https://medium.com/nerd-for-tech/redis-getting-notified-when-a-key-is-expired-or-changed-ca3e1f1c7f0a
# https://tech.webinterpret.com/redis-notifications-python/
# https://redis.io/docs/manual/keyspace-notifications/

import os
import sys
import time
import json
import redis
import signal

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_shutdown = False
g_debug_python = False

usleep = lambda x: time.sleep(x/1000000.0)

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def alpaca_1minbars_save_price(r, symbol, cp):
	key = f'DASHBOARD:DATA:CURRENTPRICE:{symbol}'
	result = r.set(key, cp)
	if result:
		print(f'SET {key:<20} ${cp}', flush=True)
	else:
		eprint(f'SET {key:<20} FAILED!')

def alpaca_handle_new_1minbar(r, key, symbol):
	val = r.get(key)
	bar = json.loads(val)
	cp = bar['c']
	alpaca_1minbars_save_price(r, symbol, cp)

# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:ALPACA:UPDATED',   'data': 'ALPACA:1MINBARS:{symbol}'}
# {'type': 'message', 'pattern': None, 'channel': 'SOURCE:ALPACA:UPDATED',   'data': 'ALPACA:DAILYBARS:{symbol}'}
def handle_channel_message(r, p, msg_obj):
#	print(msg_obj['channel'])
	key = msg_obj['data']
	symbol = key.split(':')[2]
	if key.startswith('ALPACA:1MINBARS:'):
		alpaca_handle_new_1minbar(r, key, symbol)

def channel_handler(r, p, msg_obj):
	if (msg_obj['type'] == 'message'):
		handle_channel_message(r, p, msg_obj)
	else:
		print(msg_obj, flush=True)

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

if __name__ == "__main__":
	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)
	p = r.pubsub()
	p.subscribe(f'SOURCE:ALPACA:UPDATED')

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	while not g_shutdown:
		msg = p.get_message()
		if msg: channel_handler(r, p, msg)
		else: usleep(1000)
