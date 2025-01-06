#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import redis
import datetime

import pytz
#g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

# We should get the DTR value for the symbol
# and we should ignore the symbol if its DTR is less than zero
# Assign each symbol to a specific week
# If symbol has already reported, put them in 'r'
def update_ecal(days_away_int, symbol):
	key = f'DASHBOARD:DATA:DAYSTILLREPORT:{symbol}'
	dtr_str = r.get(key)
	if dtr_str is None: return
	dtr_val = dtr_str.split(' ')[0]
	dtr = int(dtr_val)
	if (dtr < 0):
		print(f'{symbol:<6} {dtr:>3} DTR')
		week = 'r'
	elif(days_away_int < 7*1): week = '1w'
	elif(days_away_int < 7*2): week = '2w'
	elif(days_away_int < 7*3): week = '3w'
	elif(days_away_int < 7*4): week = '4w'
	elif(days_away_int < 7*5): week = '5w'
	elif(days_away_int < 7*6): week = '6w'
	else: return

	report_list = g_earnings_cal_by_week[week]
	report_list.append(symbol)

def calc_days_until(target_date, ref_date):
	diff = f'{target_date-ref_date}'
	if diff == '0:00:00': diff_str = '0 days'
	else: diff_str = diff.split(',')[0]
	days_away_str = diff_str.split(' ')[0]
	days_away_int = int(days_away_str)
	return days_away_int

# Find all the companies reporting within 6 weeks of the Sunday reference point
def handle_earnings_report_date(symbol, report_date_str):
	report_date = datetime.date.fromisoformat(report_date_str)
	days_away_int = calc_days_until(report_date, g_sunday)
	if (days_away_int > 0) and (days_away_int < 43):
#		print(f'{symbol:<6} {report_date} {days_away_int:>3}')
		update_ecal(days_away_int, symbol)

# Return date object of the most relevant Sunday reference point
def get_sunday_reference():
#	Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
	day_num_of_week = g_today.weekday()

#	Calculate how far we are away from the most relevant Sunday
#	if we are mid-trading week, we start with the Sunday before the trading week
#	Once we hit Saturday, we start calcualting from tomorrow's Sunday
	if (day_num_of_week >= 5):
		days_offest = (6-day_num_of_week)
	else:
		days_offest = -1*(day_num_of_week+1)

	sunday = g_today + datetime.timedelta(days=days_offest)
	print(f'Today:  {g_today}\nSunday: {sunday}\n')
	return sunday

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

	now_et_str = datetime.datetime.now(g_tz_et).strftime('%Y-%m-%d')
	g_today = datetime.date.fromisoformat(now_et_str)

	g_sunday = get_sunday_reference()
	g_earnings_cal_by_week = { 'r':[], '1w':[], '2w':[], '3w':[], '4w':[], '5w':[], '6w':[] }

	searchpattern = f'YFINANCE:CALENDAR:STOCK:*'
	for key in sorted(r.scan_iter(searchpattern)):
		symbol = key.split(':')[3]
		edates_str = r.get(key)
		if edates_str is None:
#			print(f'None: {symbol}')
			continue
		edates_list = json.loads(edates_str)
		if(len(edates_list) == 0):
#			print(f'Empty: {symbol}')
			continue

		report_date_str = edates_list[0]
		handle_earnings_report_date(symbol, report_date_str)

	for k,v in g_earnings_cal_by_week.items():
		symbols_reporting_this_week_str = ','.join(v)
		print(k, symbols_reporting_this_week_str)
#		key = f'DASHBOARD:DATA:ERCAL:{k}'
#		r.set(key, symbols_reporting_this_week_str)
