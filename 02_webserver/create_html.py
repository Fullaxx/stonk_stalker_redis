#!/usr/bin/env python3

import os
import sys
import time

sys.path.append('.')
sys.path.append('/app')
from ss_cfg import read_ss_config

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def write_to_file(text, filename):
	with open(filename, 'w') as f:
		f.write(text)
		f.close()

def gen_html_table(k, v, dc):
	table_name = v['TABLENAME']
	table_type = v['TABLETYPE']
	symbols_str = v['SYMBOLS']
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
	dark_theme = False
	json_fetch_interval = 5000

	dash_config = cfg['DASHBOARD_CONFIG']
	if 'THEME' in dash_config:
		if (dash_config['THEME'] == 'dark'): dark_theme = True
	if 'JSON_FETCH_INTERVAL' in dash_config:
		interval = dash_config['JSON_FETCH_INTERVAL']
		if (type(interval) == int):
			if (interval > 0): json_fetch_interval = interval

	html = '<head>'
	html += '<title>Stonk Stalker</title>'
	if dark_theme:
		html += '<link rel="stylesheet" href="static/dashboard-dark.css">'
	else:
		html += '<link rel="stylesheet" href="static/dashboard.css">'
	html += '<script src="static/jquery-3.7.1.min.js"></script>'
	html += '<script src="static/wall_clock.js"></script>'
	html += '<script src="static/market_data.js"></script>'
	html += '<script>$(document).ready(function(){ time_init(); });</script>'
	html += '<script>$(document).ready(function(){ market_data_init(' + str(json_fetch_interval) + '); });</script>'
	html += '</head>'
	return html

def gen_html_body(cfg):
	html = '<body>'
	html += '<center>'
	html += '<h2>Stonk Stalker</h2>'
	html += '<h3><div id="time"></div></h3>'

	dash_config = cfg['DASHBOARD_CONFIG']
	for k,v in cfg.items():
		if k.startswith('TABLE_'):
			html += gen_html_table(k,v,dash_config)
	html += '<a href="https://github.com/Fullaxx/stonk_stalker_redis">Source Code on GitHub</a>'
	html += '</center>'
	html += '</body>'
	return html

def gen_index_html(cfg):
	html = '<!DOCTYPE html>'
	html += '<html lang="en">'
	html += gen_html_head(cfg)
	html += gen_html_body(cfg)
	html += '</html>'
	write_to_file(html, 'index.html')

if __name__ == '__main__':
	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)

	ss_config = read_ss_config()
	gen_index_html(ss_config)
	time.sleep(2)
#	Sleep for a bit so supervisord knows all is well
