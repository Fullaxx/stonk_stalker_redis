#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import redis

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def write_to_file(text, filename):
	with open(filename, 'w') as f:
		f.write(text)
		f.close()

def create_er_cal_list():
	html = ''

	earnings_bundle_str = g_rc.get('DASHBOARD:DATA:ERCAL:BUNDLE')
	if earnings_bundle_str is None: return html
	ercal = json.loads(earnings_bundle_str)

	html += '<table id=ercallist hidden>'
	html += '<tr><th colspan=3>Upcoming Earnings Calendar List</th></tr>'
	for w in ['pr', '1w', '2w', '3w', '4w', '5w', '6w']:
		this_week = ercal[w]
		if (len(this_week) == 0):
			html += f'<tr><td>{w}</td><td></td><td></td></tr>'
		else:
			for k,v in this_week.items():
				day = v['day']
				symbols = v['symbols']
				html += f'<tr><td>{w}</td><td>{k} {day}</td><td class=ercal_symbols>{symbols}</td></tr>'

	html += '</table>'

	return html

def todays_reports(this_week, day):
	for k,v in this_week.items():
		if (v['day'] == day):
			return v['symbols']
	return ''

def create_er_cal_grid():
	html = ''

	earnings_bundle_str = g_rc.get('DASHBOARD:DATA:ERCAL:BUNDLE')
	if earnings_bundle_str is None: return html
	ercal = json.loads(earnings_bundle_str)

	html += '<table id=ercalgrid>'
	html += '<tr><th colspan=6>Upcoming Earnings Calendar Grid</th></tr>'
	html += f'<tr><th>Week</th><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th></tr>'
	for w in ['1w', '2w', '3w', '4w', '5w', '6w']:
		this_week = ercal[w]
		html += f'<tr>'
		html += f'<td>{w}</td>'
		for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
			symbols_str = todays_reports(this_week, day)
			html += f'<td class=ercal_symbols>{symbols_str}</td>'
		html += f'</tr>'

	html += '</table>'

	return html

def create_mini_cal():
	html = ''

	green_months_list = ['Jan', 'Jul']
	red_months_list = ['Apr', 'Jun', 'Sep', 'Oct', 'Dec']
	months_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

	html += '<table>'
	html += f'<tr><th colspan=12 id=marketclock>MARKETCLOCK</th></tr>'
	html += f'<tr><th colspan=12 id=marketstatus>MARKETSTATUSINIT</th></tr>'

	html += '<tr>'
	for month in months_list:
		if month in red_months_list:
			html += f'<td class=redmonth>{month}</td>'
		elif month in green_months_list:
			html += f'<td class=greenmonth>{month}</td>'
		else:
			html += f'<td>{month}</td>'
	html += '</tr>'

	html += '</table>'

	return html

def gen_html_table(k, table_name, table_type, symbols_str, dc):
	symbols_list = symbols_str.split(',')

	html = '<table>'

	html += '<tr>'
	html += f'<th><u>{table_name}</u></th>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		yfsymb = fsymb.replace('^','%5E')
		html += f'<th id={fsymb}_th><a href=https://finance.yahoo.com/quote/{yfsymb}>{symb}</a></th>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>$</td>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<td id={fsymb}_currentPrice></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>%</td>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<td id={fsymb}_move></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>Close</td>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<td id={fsymb}_previousClose></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>YTD</td>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<td id={fsymb}_ytd></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>BB</td>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<td id={fsymb}_bb></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>MACD</td>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<td id={fsymb}_macd></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>SUPPORT</td>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<td id={fsymb}_support></td>'
	html += '</tr>'

	if (table_type == 'stock') or (table_type == 'crypto'):
		if dc['DISPLAY_MARKET_CAP']:
			html += '<tr>'
			html += '<td>MCap</td>'
			for symb in symbols_list:
				fsymb = symb.replace('/','-')
				html += f'<td id={fsymb}_mcap></td>'
			html += '</tr>'

	if (table_type == 'stock'):
		if dc['DISPLAY_FPE_RATIO']:
			html += '<tr>'
			html += '<td>FPE</td>'
			for symb in symbols_list:
				fsymb = symb.replace('/','-')
				html += f'<td id={fsymb}_forwardPE></td>'
			html += '</tr>'

		if dc['DISPLAY_PST12_RATIO']:
			html += '<tr>'
			html += '<td>PST12</td>'
			for symb in symbols_list:
				fsymb = symb.replace('/','-')
				html += f'<td id={fsymb}_priceToSalesTrailing12Months></td>'
			html += '</tr>'

		if dc['DISPLAY_PEG_RATIO']:
			html += '<tr>'
			html += '<td>tPEG</td>'
			for symb in symbols_list:
				fsymb = symb.replace('/','-')
				html += f'<td id={fsymb}_trailingPegRatio></td>'
			html += '</tr>'

		if dc['DISPLAY_PB_RATIO']:
			html += '<tr>'
			html += '<td>PB</td>'
			for symb in symbols_list:
				fsymb = symb.replace('/','-')
				html += f'<td id={fsymb}_pbRatio></td>'
			html += '</tr>'

		if dc['DISPLAY_DTR']:
			html += '<tr>'
			html += '<td>DTR</td>'
			for symb in symbols_list:
				fsymb = symb.replace('/','-')
				html += f'<td id={fsymb}_dtr></td>'
			html += '</tr>'

	if dc['DISPLAY_OTHER_URLS']:
		html += '<tr>'
		html += '<td>URLS</td>'
		for symb in symbols_list:
			yfsymb = symb.replace('/','-').replace('^','%5E')
			gfsymb = symb.replace('/','-').replace('^','%5E')
			html += f'<td><a href=https://finance.yahoo.com/quote/{yfsymb}>YF</a>/<a href=https://gurufocus.com/stock/{gfsymb}>GF</a></td>'
		html += '</tr>'

	html += '</table>'
	return html

def get_total_symbols():
	stocks_count = g_rc.scard('DASHBOARD:SYMBOLS_SET:STOCKS')
	crypto_count = g_rc.scard('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_count = g_rc.scard('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_count = g_rc.scard('DASHBOARD:SYMBOLS_SET:ETF')
	future_count = g_rc.scard('DASHBOARD:SYMBOLS_SET:FUTURE')
	return int(stocks_count) + int(crypto_count) + int(index_count) + int(etf_count) + int(future_count)

def gen_html_body():
#	Get total count of symbols we are tracking
	symbols_count = get_total_symbols()

	html = '<body>'
	html += '<center>'
	html += f'<p class=titleheader>Stonk Stalker ({symbols_count} Symbols)</p>'

	dc = g_cfg['DASHBOARD_CONFIG']
	if dc['PAGE_HEADER_TYPE'] == 'simple':
		html += '<p class=standalonemarketclock id=marketclock></p>'
	if dc['PAGE_HEADER_TYPE'] == 'calendars':
		html += create_mini_cal()
		html += '<br>'
		html += f'<button onclick="toggleGridHidden()" type="button">Toggle Grid</button>'
		html += f'<button onclick="toggleListHidden()" type="button">Toggle List</button>'
		html += '<br>'
		html += create_er_cal_list()
		html += '<br>'
		html += create_er_cal_grid()

#	Horizontal Seperator
	html += '<hr>'

	for k,v in g_cfg.items():
		if k.startswith('TABLE_'):
			table_name = v['TABLENAME']
			table_type = v['TABLETYPE']
			if (table_type == 'index'):
				key = f'DASHBOARD:TABLES:INDEX:{table_name}'
			if (table_type == 'etf'):
				key = f'DASHBOARD:TABLES:ETF:{table_name}'
			if (table_type == 'future'):
				key = f'DASHBOARD:TABLES:FUTURE:{table_name}'
			if (table_type == 'crypto'):
				key = f'DASHBOARD:TABLES:SORTED:MCAP:{table_name}'
			if (table_type == 'stock'):
				key = f'DASHBOARD:TABLES:SORTED:MCAP:{table_name}'
			symbols_str = g_rc.get(key)
			html += gen_html_table(k, table_name, table_type, symbols_str, dc)
			html += '<br>'

	html += '<a href="https://github.com/Fullaxx/stonk_stalker_redis">Source Code on GitHub</a>'
	html += '</center>'
	html += '</body>'
	return html

def gen_html_head():
	dash_config = g_cfg['DASHBOARD_CONFIG']
	json_fetch_interval = dash_config['JSON_FETCH_INTERVAL']
	dashboard_theme = dash_config['THEME']

	html = '<head>'
	html += '<meta charset="utf-8">'
	html += '<title>Stonk Stalker</title>'
	if (dashboard_theme == 'dark'):
		html += '<link rel="stylesheet" href="static/dashboard-dark.css">'
	else:
		html += '<link rel="stylesheet" href="static/dashboard.css">'
	html += '<script src="static/jquery-3.7.1.min.js"></script>'
	html += '<script src="static/market_clock.js"></script>'
	html += '<script>$(document).ready(function(){ market_clock_init(); });</script>'
	html += '<script>$(document).ready(function(){ market_status_init(); });</script>'
	html += '<script src="static/market_calendars.js"></script>'
	html += '<script>$(document).ready(function(){ market_calendars_init(); });</script>'
	html += '<script src="static/market_data.js"></script>'
	html += '<script>$(document).ready(function(){ market_data_init(' + str(json_fetch_interval) + '); });</script>'
	html += '</head>'
	return html

def gen_index_html():
	html = '<!DOCTYPE html>'
	html += '<html lang="en">'
	html += gen_html_head()
	html += gen_html_body()
	html += '</html>'
	write_to_file(html, 'index.html')

def acquire_environment():
	global g_debug_python

	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)

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
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)

	wait_for_ready(g_rc, 'DASHBOARD:READY', 0.1)

	cfg_str = g_rc.get('DASHBOARD:CONFIG')
	g_cfg = json.loads(cfg_str)
	gen_index_html()
