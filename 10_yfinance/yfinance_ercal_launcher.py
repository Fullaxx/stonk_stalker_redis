#!/usr/bin/env python3

import os
import sys
import time
import signal
import datetime

import pytz
#g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

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

def every_halfhour():
	hourmin = g_now_dt.strftime('%H%M')
	if (hourmin == '0130'):
		os.system(f'./ercal2redis.py')
		print(f'yfinance_ercal_launcher: @{hourmin} Launching ./ercal2redis.py')

def chdir_if_production():
	if os.path.exists('/app'):
		ercal2redis = os.path.exists('/app/ercal2redis.py')
		yfercl = os.path.exists('/app/yfinance_ercal_launcher.py')
		if (ercal2redis and yfercl):
			os.chdir('/app')

def acquire_environment():
	global g_debug_python

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

if __name__ == '__main__':
	chdir_if_production()
	acquire_environment()

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

#	g_last_sec_trigger = 0
#	g_last_min_trigger = 0
	g_last_halfhour_trigger = 0
#	g_last_hour_trigger = 0
	while not g_shutdown:
		g_now_dt = datetime.datetime.now(g_tz_et)
		g_now_s = int(g_now_dt.timestamp())
#		if (g_now_s > g_last_sec_trigger):
#			every_second()
#			g_last_sec_trigger = g_now_s
#		if ((g_now_s % 60) == 0):
#			if (g_now_s > g_last_min_trigger):
#				every_minute(g_now_z)
#				g_last_min_trigger = g_now_s
		if ((g_now_s % 1800) == 0):
			if (g_now_s > g_last_halfhour_trigger):
				every_halfhour()
				g_last_halfhour_trigger = g_now_s
#		if ((g_now_s % 3600) == 0):
#			if (g_now_s > g_last_hour_trigger):
#				every_hour()
#				g_last_hour_trigger = g_now_s

		time.sleep(0.1)
