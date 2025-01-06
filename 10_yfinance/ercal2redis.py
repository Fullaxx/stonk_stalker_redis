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

def calc_days_until(target_date, ref_date):
	diff = f'{target_date-ref_date}'
	if diff == '0:00:00': diff_str = '0 days'
	else: diff_str = diff.split(',')[0]
	days_away_str = diff_str.split(' ')[0]
	days_away_int = int(days_away_str)
	return days_away_int

def update_earnings_report_by_date_dict(symbol, report_date_str):
#	Limit our catalog to relevant earnings reports (6w from the reference Sunday)
	report_date = datetime.date.fromisoformat(report_date_str)
	days_away_int = calc_days_until(report_date, g_sunday)
	if (days_away_int < 0) or (days_away_int > 42):
		return

	if report_date_str not in g_earnings_cal_by_date:
		g_earnings_cal_by_date[report_date_str] = []

	date_list = g_earnings_cal_by_date[report_date_str]
	date_list.append(symbol)

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

def which_day_of_week(report_date):
	day_num = report_date.weekday()
	if   (day_num == 0): return 'Mon'
	elif (day_num == 1): return 'Tue'
	elif (day_num == 2): return 'Wed'
	elif (day_num == 3): return 'Thu'
	elif (day_num == 4): return 'Fri'
	elif (day_num == 5): return 'Sat'
	elif (day_num == 6): return 'Sun'
	return None

# pr means past report (-1 days away or more)
def save_week(start, stop, week):
	key = f'DASHBOARD:DATA:ERCAL:{week}'
	print(key)

	this_week_cell_data = ''
	for i in range(start, stop):
		report_date = g_sunday + datetime.timedelta(days=i)
		day_of_week = which_day_of_week(report_date)
		days_until = calc_days_until(report_date, g_today)

#		If we are looking for past earnings reports, skip over anything in the future
		if (week == 'pr') and (days_until >= 0): continue

#		If we are looking for future earnings reports, skip over anything in the past
		if (week != 'pr') and (days_until  < 0): continue

		report_date_str = report_date.strftime('%Y-%m-%d')
		if report_date_str in g_earnings_cal_by_date:
			symbols_reporting = g_earnings_cal_by_date[report_date_str]
			print(f'{report_date_str}: {symbols_reporting}')
			this_week_cell_data += f'{day_of_week} {report_date_str}: ' + ', '.join(symbols_reporting) + '</br>'

	print()
	r.set(key, this_week_cell_data)

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
	g_earnings_cal_by_date = {}

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
		update_earnings_report_by_date_dict(symbol, report_date_str)

	save_week(0,   7, 'pr')
	save_week(0,   7, '1w')
	save_week(8,  14, '2w')
	save_week(15, 21, '3w')
	save_week(22, 28, '4w')
	save_week(29, 35, '5w')
	save_week(36, 42, '6w')
