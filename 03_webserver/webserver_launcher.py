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

def launch_script(path, now_z, verbose):
	if (g_debug_python or verbose):
		now_et = now_z.astimezone(g_tz_et)
		timestamp_str = now_et.strftime('%Y-%m-%d %H:%M:%S')
		print(f'{timestamp_str}: {path}', flush=True)
	os.system(path)

#	Get the most recent value for ALPACA:MARKET:NEXTOPEN:ZSTAMP from redis
#	If it has changed, print a message and update g_nextopen_zs
def update_next_open(r, now_z, now_s):
	global g_nextopen_zs

	nextopen_zstamp_str = r.get('ALPACA:MARKET:NEXTOPEN:ZSTAMP')
	if nextopen_zstamp_str is None: return
	nextopen_zs = int(nextopen_zstamp_str)
	if (nextopen_zs != g_nextopen_zs):
		g_nextopen_zs = nextopen_zs
		nosa = g_nextopen_zs - now_s
		now_et = now_z.astimezone(g_tz_et)
		log_timestamp_str = now_et.strftime('%Y-%m-%d %H:%M:%S')
		print(f'{log_timestamp_str}: next_open={g_nextopen_zs} {nosa} seconds away', flush=True)

#	Calculate how far away we are from the market open using g_next_open_timestamp
#	If we are within 1 second, launch ./update_prevclose.py
def prepare_for_upcoming_market_open(now_z, now_s):
	global g_nextopen_zs
	if (g_nextopen_zs == 0): return
	nosa = g_nextopen_zs - now_s
	if g_debug_python:
		print(f'{nosa} seconds away')
	if (nosa == 1):
		launch_script('./update_prevclose.py', now_z, True)

def every_hour(r, now_z):
	launch_script('./create_html.py', now_z, True)

def every_halfhour(now_z, now_s):
	update_next_open(r, now_z, now_s)

#def every_minute(now_z):
#	pass

def every_second(now_z, now_s):
	global g_last_mdjc_trigger

	prepare_for_upcoming_market_open(now_z, now_s)
	launch_script('./create_market_status_json.py', now_z, False)
	if (now_s >= (g_last_mdjc_trigger + g_market_json_creation_interval)):
		launch_script('./create_market_data_json.py', now_z, False)
		g_last_mdjc_trigger = now_s

#	Load MARKET_DATA_CREATE_INTERVAL from config
def load_market_json_creation_interval(r):
	cfg_str = r.get('DASHBOARD:CONFIG')
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
	r = connect_to_redis(redis_url, True, False, g_debug_python)

	if g_wait_for_ready:
		wait_for_ready(r, 'DASHBOARD:READY', 0.1)

	g_market_json_creation_interval = load_market_json_creation_interval(r)

#	Tasks to do once at startup
	now_z = datetime.datetime.now(g_tz_utc)
	now_s = int(now_z.timestamp())
	update_next_open(r, now_z, now_s)
	launch_script('./create_html.py', now_z, False)
	launch_script('./create_market_status_json.py', now_z, False)
	launch_script('./create_market_data_json.py', now_z, False)
	g_last_mdjc_trigger = int(now_z.timestamp())

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	g_last_sec_trigger = 0
#	g_last_min_trigger = 0
	g_last_halfhour_trigger = 0
	g_last_hour_trigger = 0
	while not g_shutdown:
		now_z = datetime.datetime.now(g_tz_utc)
		now_s = int(now_z.timestamp())
		if (now_s > g_last_sec_trigger):
			every_second(now_z, now_s)
			g_last_sec_trigger = now_s
#		if ((now_s % 60) == 0):
#			if (now_s > g_last_min_trigger):
#				every_minute(now_z)
#				g_last_min_trigger = now_s
		if ((now_s % 1800) == 0):
			if (now_s > g_last_halfhour_trigger):
				every_halfhour(now_z)
				g_last_halfhour_trigger = now_s
		if ((now_s % 3600) == 0):
			if (now_s > g_last_hour_trigger):
				every_hour(r, now_z)
				g_last_hour_trigger = now_s

		usleep(1000)
