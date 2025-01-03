#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import time
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

def create_mini_cal():
	green_months_list = ['Jan', 'Jul']
	red_months_list = ['Apr', 'Jun', 'Sep', 'Oct', 'Dec']
	months_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

	html = ''
	html += '<h3><div id=minical>'
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
	html += '</div></h3>'
	html += '<hr>'
	return html

def gen_html_table(k, table_name, table_type, symbols_str, dc):
	symbols_list = symbols_str.split(',')

	html = '<table>'

	html += '<tr>'
	html += f'<th><u>{table_name}</u></th>'
	for symb in symbols_list:
		fsymb = symb.replace('/','-')
		html += f'<th id={fsymb}_th><a href=https://finance.yahoo.com/quote/{fsymb}>{symb}</a></th>'
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
			yfsymb = symb.replace('/','-')
			gfsymb = symb.replace('/','-')
			html += f'<td><a href=https://finance.yahoo.com/quote/{yfsymb}>YF</a>/<a href=https://gurufocus.com/stock/{gfsymb}>GF</a></td>'
		html += '</tr>'

	html += '</table>'
	html += '</br>'
	return html

def gen_html_head(cfg):
	dash_config = cfg['DASHBOARD_CONFIG']
	json_fetch_interval = dash_config['JSON_FETCH_INTERVAL']
	dashboard_theme = dash_config['THEME']

	html = '<head>'
	html += '<title>Stonk Stalker</title>'
	if (dashboard_theme == 'dark'):
		html += '<link rel="stylesheet" href="static/dashboard-dark.css">'
	else:
		html += '<link rel="stylesheet" href="static/dashboard.css">'
	html += '<script src="static/jquery-3.7.1.min.js"></script>'
	html += '<script src="static/market_clock.js"></script>'
	html += '<script src="static/market_data.js"></script>'
	html += '<script>$(document).ready(function(){ market_clock_init(); });</script>'
	html += '<script>$(document).ready(function(){ market_status_init(); });</script>'
	html += '<script>$(document).ready(function(){ market_data_init(' + str(json_fetch_interval) + '); });</script>'
	html += '</head>'
	return html

def get_total_symbols(r):
	stocks_count = r.scard('DASHBOARD:SYMBOLS_SET:STOCKS')
	crypto_count = r.scard('DASHBOARD:SYMBOLS_SET:CRYPTO')
	index_count = r.scard('DASHBOARD:SYMBOLS_SET:INDEX')
	etf_count = r.scard('DASHBOARD:SYMBOLS_SET:ETF')
	future_count = r.scard('DASHBOARD:SYMBOLS_SET:FUTURE')
	return int(stocks_count) + int(crypto_count) + int(index_count) + int(etf_count) + int(future_count)

def gen_html_body(r, cfg):
#	Get total count of symbols we are tracking
	symbols_count = get_total_symbols(r)

	html = '<body>'
	html += '<center>'
	html += f'<h2>Stonk Stalker ({symbols_count} Symbols)</h2>'

	dc = cfg['DASHBOARD_CONFIG']
	if dc['DISPLAY_MINI_CALENDAR']:
		html += create_mini_cal()
	else:
		html += '<h3><div id=time></div></h3>'

	for k,v in cfg.items():
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
			symbols_str = r.get(key)
			html += gen_html_table(k, table_name, table_type, symbols_str, dc)

	html += '<a href="https://github.com/Fullaxx/stonk_stalker_redis">Source Code on GitHub</a>'
	html += '</center>'
	html += '</body>'
	return html

def gen_index_html(r, cfg):
	html = '<!DOCTYPE html>'
	html += '<html lang="en">'
	html += gen_html_head(cfg)
	html += gen_html_body(r, cfg)
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
	r = connect_to_redis(redis_url, True, False, g_debug_python)

	wait_for_ready(r, 'DASHBOARD:READY', 0.1)

	cfg_str = r.get('DASHBOARD:CONFIG')
	ss_config = json.loads(cfg_str)
	gen_index_html(r, ss_config)
	time.sleep(3)
#	Sleep for a bit so supervisord knows all is well
