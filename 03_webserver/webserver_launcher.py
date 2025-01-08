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
g_last_nextopen_str = None
g_next_open_timestamp = None

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

#	Get the most recent value for ALPACA:MARKET:CLOCK:JSON from redis
#	If it has changed, print a message and update g_next_open_timestamp
def update_next_open(r, now_z):
	global g_last_nextopen_str, g_next_open_timestamp

	changed = False
	market_clock_str = r.get('ALPACA:MARKET:CLOCK:JSON')
	if market_clock_str is None: return
	market_clock = json.loads(market_clock_str)
	nextopen_str = market_clock['next_open']

	if g_last_nextopen_str is None:
		changed = True
		g_last_nextopen_str = nextopen_str
	elif (nextopen_str != g_last_nextopen_str):
		changed = True

	if changed:
		now_et = now_z.astimezone(g_tz_et)
		timestamp_str = now_et.strftime('%Y-%m-%d %H:%M:%S')
		print(f'{timestamp_str}: next_open={nextopen_str}', flush=True)

	next_open_et = datetime.datetime.strptime(nextopen_str, '%Y-%m-%dT%H:%M:%S%z')
	now_unix_float = next_open_et.astimezone(g_tz_utc).timestamp()
	g_next_open_timestamp = int(now_unix_float)

#	Calculate how far away we are from the market open using g_next_open_timestamp
#	If we are within 1 second, launch ./update_prevclose.py
def check_for_upcoming_market_open(now_z):
	global g_next_open_timestamp
	if (g_next_open_timestamp is None): return
	now_s = int(now_z.timestamp())
	next_open_seconds_away = g_next_open_timestamp - now_s
	if g_debug_python: print(f'{next_open_seconds_away} seconds away')
	if (next_open_seconds_away == 1):
		launch_script('./update_prevclose.py', now_z, True)

def every_hour(r, now_z):
	update_next_open(r, now_z)
	launch_script('./create_html.py', now_z, True)

#def every_halfhour(now_z):
#	pass
#
#def every_minute(now_z):
#	pass

def every_second(now_z, now_s):
	global g_last_mdjc_trigger

	check_for_upcoming_market_open(now_z)
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
	now_dt = datetime.datetime.now(g_tz_utc)
	update_next_open(r, now_dt)
	launch_script('./create_html.py', now_dt, False)
	launch_script('./create_market_status_json.py', now_dt, False)
	launch_script('./create_market_data_json.py', now_dt, False)
	g_last_mdjc_trigger = int(now_dt.timestamp())

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	g_last_sec_trigger = 0
#	g_last_min_trigger = 0
#	g_last_halfhour_trigger = 0
	g_last_hour_trigger = 0
	while not g_shutdown:
		now_dt = datetime.datetime.now(g_tz_utc)
		now_s = int(now_dt.timestamp())
		if (now_s > g_last_sec_trigger):
			every_second(now_dt, now_s)
			g_last_sec_trigger = now_s
#		if ((now_s % 60) == 0):
#			if (now_s > g_last_min_trigger):
#				every_minute(now_dt)
#				g_last_min_trigger = now_s
#		if ((now_s % 1800) == 0):
#			if (now_s > g_last_halfhour_trigger):
#				every_halfhour(now_dt)
#				g_last_halfhour_trigger = now_s
		if ((now_s % 3600) == 0):
			if (now_s > g_last_hour_trigger):
				every_hour(r, now_dt)
				g_last_hour_trigger = now_s

		usleep(1000)
