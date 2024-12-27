#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import time
import redis
import signal

from datetime import datetime
from pathlib import Path

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def publish_ready(r, v):
	r.set('DASHBOARD:READY', 'READY', ex=5)
	if v: print(f'READY!', flush=True)

def prepare_config(cfg):
	if 'DASHBOARD_CONFIG' not in cfg:
		cfg['DASHBOARD_CONFIG'] = {
			'THEME' : 'light',
			'MARKET_DATA_CREATE_INTERVAL' : 5,
			'JSON_FETCH_INTERVAL' : 4000,
			'DISPLAY_MARKET_CAP' : False,
			'DISPLAY_FPE_RATIO' : False,
			'DISPLAY_PST12_RATIO' : False,
			'DISPLAY_PEG_RATIO' : False,
			'DISPLAY_PB_RATIO' : False,
			'DISPLAY_OTHER_URLS' : False,
		}

	return cfg

def read_config():
	cfg_dir = Path('/config')
	if not cfg_dir.is_dir():
		bailmsg(f'/config is not a directory!')
	cfg_file = Path('/config/dashboard_config.json')
	if not cfg_file.is_file():
		bailmsg(f'/config/dashboard_config.json is not a file!')

	with open('/config/dashboard_config.json', 'r') as f:
		config_str = f.read()
		return json.loads(config_str)

	return None

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

#	Prepare Config
	ss_config = read_config()
	prepared_config = prepare_config(ss_config)

#	Publish Config
	key = 'DASHBOARD:CONFIG'
	cfg_str = json.dumps(prepared_config)
	r.set(key, cfg_str)

#	Sort Tables
	os.system('/app/sort_tables.py')

#	Inform others that we are ready
	publish_ready(r, True)

#	Prepare Signals
	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

#	Wait for the slow release of death
	next = 0
	while not g_shutdown:
		now_dt = datetime.utcnow()
		now_s = int(now_dt.timestamp())
		if (now_s >= next):
			publish_ready(r, False)
			next = now_s + 2
		time.sleep(0.1)

	r.delete('DASHBOARD:READY')
