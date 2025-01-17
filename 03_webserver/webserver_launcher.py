#!/usr/bin/env python3

import os
import sys
import json
import redis
import signal
import datetime

import pytz
g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

import time
usleep = lambda x: time.sleep(x/1000000.0)

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False
g_wait_for_ready = True
g_nextopen_zs = 0

g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def launch_script(path, verbose):
	if (g_debug_python or verbose):
		now_et = g_now_z.astimezone(g_tz_et)
		timestamp_str = now_et.strftime('%Y-%m-%d %H:%M:%S')
		print(f'{timestamp_str}: {path}', flush=True)
	os.system(path)

# Get the most recent value for ALPACA:MARKET:NEXTOPEN:ZSTAMP from redis
# If it has changed, print a message and update g_nextopen_zs
def update_next_open():
	global g_nextopen_zs

	nextopen_zstamp_str = g_rc.get('ALPACA:MARKET:NEXTOPEN:ZSTAMP')
	if nextopen_zstamp_str is None: return
	nextopen_zs = int(nextopen_zstamp_str)
	if (nextopen_zs != g_nextopen_zs):
		g_nextopen_zs = nextopen_zs
		nosa = g_nextopen_zs - g_now_s
		now_et = g_now_z.astimezone(g_tz_et)
		log_timestamp_str = now_et.strftime('%Y-%m-%d %H:%M:%S')
		nextopen_z = datetime.datetime.fromtimestamp(g_nextopen_zs, tz=pytz.UTC)
		nextopen_et = nextopen_z.astimezone(g_tz_et)
		print(f'{log_timestamp_str}: next_open={g_nextopen_zs} {nosa} seconds away @ {nextopen_et}', flush=True)

# Calculate how far away we are from the market open using g_next_open_timestamp
# If we are within 1 second, launch ./update_prevclose.py
def prepare_for_upcoming_market_open():
	nosa = g_nextopen_zs - g_now_s
	if g_debug_python:
		print(f'{nosa} seconds away')
	if (nosa == 4):
		launch_script('./update_prevclose.py', True)

def check_for_crypto_day_rollover():
	hms = g_now_z.strftime('%H%M%S')
	if (hms == '000000'):
		launch_script('./update_prevclose.py --crypto', True)

def every_60m():
	launch_script('./create_html.py', True)

def every_30m():
	update_next_open()

#def every_60s():
#	pass

def every_1s():
	global g_last_mdjc_trigger

	check_for_crypto_day_rollover()
	prepare_for_upcoming_market_open()
	launch_script('./create_market_status_json.py', False)
	if (g_now_s >= (g_last_mdjc_trigger + g_market_json_creation_interval)):
		launch_script('./create_market_data_json.py', False)
		g_last_mdjc_trigger = g_now_s

# Load MARKET_DATA_CREATE_INTERVAL from config
def load_market_json_creation_interval():
	cfg_str = g_rc.get('DASHBOARD:CONFIG')
	ss_config = json.loads(cfg_str)
	dash_config = ss_config['DASHBOARD_CONFIG']
	interval = dash_config['MARKET_DATA_CREATE_INTERVAL']
	print(f'Will update market data json every {interval} seconds', flush=True)
	return interval

def acquire_environment():
	global g_wait_for_ready, g_debug_python

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	swfr_env_var = os.getenv('WAIT_FOR_READY')
	if swfr_env_var is not None:
		flags = ('0', 'n', 'N', 'f', 'F')
		if (swfr_env_var.startswith(flags)): g_wait_for_ready = False
		if (swfr_env_var == 'off'): g_wait_for_ready = False
		if (swfr_env_var == 'OFF'): g_wait_for_ready = False

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return redis_url

def chdir_if_production():
	if os.path.exists('/app'):
		che = os.path.exists('/app/create_html.py')
		upce = os.path.exists('/app/update_prevclose.py')
		cmsje = os.path.exists('/app/create_market_data_json.py')
		cmsje = os.path.exists('/app/create_market_status_json.py')
		if (che and upce and cmsje and cmsje):
			os.chdir('/app')

if __name__ == '__main__':
	chdir_if_production()
	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)

	if g_wait_for_ready:
		wait_for_ready(g_rc, 'DASHBOARD:READY', 0.1)

	g_market_json_creation_interval = load_market_json_creation_interval()

#	Tasks to do once at startup
	g_now_z = datetime.datetime.now(g_tz_utc)
	g_now_s = int(g_now_z.timestamp())
	update_next_open()
	launch_script('./create_html.py', False)
	launch_script('./create_market_status_json.py', False)
	launch_script('./create_market_data_json.py', False)
	g_last_mdjc_trigger = g_now_s

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	g_1s_trigger = 0
#	g_60s_trigger = 0
	g_30m_trigger = 0
	g_60m_trigger = 0
	while not g_shutdown:
		g_now_z = datetime.datetime.now(g_tz_utc)
		g_now_s = int(g_now_z.timestamp())
		if (g_now_s > g_1s_trigger):
			every_1s()
			g_1s_trigger = g_now_s
#		if ((g_now_s % 60) == 0):
#			if (g_now_s > g_60s_trigger):
#				every_60s()
#				g_60s_trigger = g_now_s
		if ((g_now_s % 1800) == 0):
			if (g_now_s > g_30m_trigger):
				every_30m()
				g_30m_trigger = g_now_s
		if ((g_now_s % 3600) == 0):
			if (g_now_s > g_60m_trigger):
				every_60m()
				g_60m_trigger = g_now_s

		usleep(1000)
