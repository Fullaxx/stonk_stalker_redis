#!/usr/bin/env python3

import os
import sys
import time
import redis
import signal
import datetime

import pytz
#g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,is_market_open

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

def every_60m():
	pass

# @ 0230a launch ercal2redis.py
def every_30m():
	hourmin = g_now_dt.strftime('%H%M')
	if (hourmin == '0230'):
#		print(f'yfinance_launcher: @{hourmin} Launching ./ercal2redis.py')
		os.system(f'./ercal2redis.py')

def every_15m():
	pass

# Every 5 minutes we will:
# * launch livebars2redis()
#   - update live crypto prices if market is closed
#   - update live crypto/index/etc/future prices if market is open
def every_5m():
#	print(f'yfinance_launcher: @{hourmin} Launching ./livebars2redis.py')
	os.system(f'./livebars2redis.py')

# Every minute that the market is closed, we will:
# * call update_random_ticker_info.py if Sat or Sun or during the hours of 2000 - 0359
# * call update_random_table_stats.py if Sat or Sun or during the hours of 2000 - 2359
def every_60s():
	if g_market_is_open: return

	day = g_today.weekday()
	hour = g_now_dt.strftime('%H')
	ticker_hours = ('20','21','22','23','00','01','02','03')
	if ((day > 4) or (hour.startswith(ticker_hours))):
		os.system(f'./update_random_ticker_info.py')
	indicators_hours = ('20','21','22','23')
	if ((day > 4) or (hour.startswith(indicators_hours))):
		os.system(f'./update_random_table_stats.py')

def every_1s():
	global g_market_is_open
	g_market_is_open = is_market_open(g_rc, 0.1)

def chdir_if_production():
	if os.path.exists('/app'):
		yfle = os.path.exists('/app/yfinance_launcher.py')
		erce = os.path.exists('/app/ercal2redis.py')
		te = os.path.exists('/app/ticker2redis.py')
		lbe = os.path.exists('/app/livebars2redis.py')
		dse = os.path.exists('/app/dailystats2redis.py')
		urtie = os.path.exists('/app/update_random_ticker_info.py')
		urtse = os.path.exists('/app/update_random_table_stats.py')
		if (yfle and erce and te and lbe and dse and urtie and urtse):
			os.chdir('/app')

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
	chdir_if_production()

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	g_market_is_open = is_market_open(g_rc, 0.1)

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	g_1s_trigger = 0
	g_60s_trigger = 0
	g_5m_trigger = 0
	g_15m_trigger = 0
	g_30m_trigger = 0
	g_60m_trigger = 0
	while not g_shutdown:
		g_now_dt = datetime.datetime.now(g_tz_et)
		g_now_s = int(g_now_dt.timestamp())
		g_today = datetime.date.fromtimestamp(g_now_s)
		if (g_now_s > g_1s_trigger):
			every_1s()
			g_1s_trigger = g_now_s
		if ((g_now_s % 60) == 0):
			if (g_now_s > g_60s_trigger):
				every_60s()
				g_60s_trigger = g_now_s
		if ((g_now_s % 300) == 0):
			if (g_now_s > g_5m_trigger):
				every_5m()
				g_5m_trigger = g_now_s
		if ((g_now_s % 900) == 0):
			if (g_now_s > g_15m_trigger):
				every_15m()
				g_15m_trigger = g_now_s
		if ((g_now_s % 1800) == 0):
			if (g_now_s > g_30m_trigger):
				every_30m()
				g_30m_trigger = g_now_s
		if ((g_now_s % 3600) == 0):
			if (g_now_s > g_60m_trigger):
				every_60m()
				g_60m_trigger = g_now_s

		time.sleep(0.1)
