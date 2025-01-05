#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import redis
import datetime

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def create_weekly_report(dtr_by_time, start, stop, week):
	print()
	symbols_list = []
	for i in range(start, stop):
		if i in dtr_by_time:
			symbols_list += dtr_by_time[i]
	print(week, symbols_list)

def update_dicts(key, val, dtr_by_symbol, dtr_by_time):
	symbol = key.split(':')[3]
	dtr_str = val.split(' ')[0]
	if(dtr_str == ''): return

	dtr = int(dtr_str, 10)
	if (dtr < 0) or (dtr > 42): return

	dtr_by_symbol[symbol] = dtr

	if dtr in dtr_by_time:
		report_list = dtr_by_time[dtr]
	else:
		report_list = []
	report_list.append(symbol)
	dtr_by_time[dtr] = report_list

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

	dtr_by_time = {}
	dtr_by_symbol = {}
	searchpattern = f'DASHBOARD:DATA:DAYSTILLREPORT:*'
	for key in sorted(r.scan_iter(searchpattern)):
		val = r.get(key)
		if val is not None:
			update_dicts(key, val, dtr_by_symbol, dtr_by_time)

#	for k,v in dtr_by_time.items():
#		print(k, v)

	for i in range(0, 42):
		if i in dtr_by_time:
			print(i, dtr_by_time[i])

	create_weekly_report(dtr_by_time, 0, 7, '1w')
	create_weekly_report(dtr_by_time, 8, 14, '2w')
	create_weekly_report(dtr_by_time, 15, 21, '3w')
	create_weekly_report(dtr_by_time, 22, 28, '4w')
	create_weekly_report(dtr_by_time, 29, 35, '5w')
	create_weekly_report(dtr_by_time, 36, 42, '6w')
