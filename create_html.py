#!/usr/bin/env python3

import os
import sys
import json
import time

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def write_to_file(text, filename):
	with open(filename, 'w') as f:
		f.write(text)
		f.close()

def gen_html_table(tbl):
	table_name,symbols = tbl.split('=')
	symb_list = symbols.split(',')

	html = '<table>'

	html += '<tr>'
	html += f'<th><u>{table_name}</u></th>'
	for symb in symb_list:
		html += f'<th id={symb}_th><a href=https://finance.yahoo.com/quote/{symb}>{symb}</a></th>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>$</td>'
	for symb in symb_list:
		html += f'<td id={symb}_currentPrice></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>%</td>'
	for symb in symb_list:
		html += f'<td id={symb}_move></td>'
	html += '</tr>'

	html += '<tr>'
	html += '<td>Close</td>'
	for symb in symb_list:
		html += f'<td id={symb}_previousClose></td>'
	html += '</tr>'

	mc_toggle = os.getenv('DISPLAY_MARKET_CAP')
	if (mc_toggle is not None) and (mc_toggle == '1'):
		html += '<tr>'
		html += '<td>MCap</td>'
		for symb in symb_list:
			html += f'<td id={symb}_mcap></td>'
		html += '</tr>'

	fpe_toggle = os.getenv('DISPLAY_FPE_RATIO')
	if (fpe_toggle is not None) and (fpe_toggle == '1'):
		html += '<tr>'
		html += '<td>FPE</td>'
		for symb in symb_list:
			html += f'<td id={symb}_forwardPE></td>'
		html += '</tr>'

	pst12_toggle = os.getenv('DISPLAY_PST12_RATIO')
	if (pst12_toggle is not None) and (pst12_toggle == '1'):
		html += '<tr>'
		html += '<td>PST12</td>'
		for symb in symb_list:
			html += f'<td id={symb}_priceToSalesTrailing12Months></td>'
		html += '</tr>'

	peg_toggle = os.getenv('DISPLAY_PEG_RATIO')
	if (peg_toggle is not None) and (peg_toggle == '1'):
		html += '<tr>'
		html += '<td>tPEG</td>'
		for symb in symb_list:
			html += f'<td id={symb}_trailingPegRatio></td>'
		html += '</tr>'

	pb_toggle = os.getenv('DISPLAY_PB_RATIO')
	if (pb_toggle is not None) and (pb_toggle == '1'):
		html += '<tr>'
		html += '<td>PB</td>'
		for symb in symb_list:
			html += f'<td id={symb}_pbRatio></td>'
		html += '</tr>'

	urls_toggle = os.getenv('OTHER_URLS')
	if (urls_toggle is not None) and (urls_toggle == '1'):
		html += '<tr>'
		html += '<td>URLS</td>'
		for symb in symb_list:
			html += f'<td><a href=https://finance.yahoo.com/quote/{symb}>YF</a>/<a href=https://gurufocus.com/stock/{symb}>GF</a></td>'
		html += '</tr>'

	html += '</table>'
	html += '</br>'
	return html

def gen_html_head(market_data_fetch_interval):
	html = '<head>'
	html += '<title>Stonk Stalker</title>'
	if os.getenv('DARKMODE'):
		html += '<link rel="stylesheet" href="static/dashboard-dark.css">'
	else:
		html += '<link rel="stylesheet" href="static/dashboard.css">'
	html += '<script src="static/jquery-3.7.1.min.js"></script>'
	html += '<script src="static/wall_clock.js"></script>'
	html += '<script src="static/market_data.js"></script>'
	html += '<script>$(document).ready(function(){ time_init(); });</script>'
	html += '<script>$(document).ready(function(){ market_data_init(' + market_data_fetch_interval + '); });</script>'
	html += '</head>'
	return html

def gen_html_body():
	html = '<body>'
	html += '<center>'
	html += '<h2>Stonk Stalker</h2>'
	html += '<h3><div id="time"></div></h3>'
	for tbl in tables_list:
		html += gen_html_table(tbl)
	html += '<a href="https://github.com/Fullaxx/stonk_stalker_redis">Source Code on GitHub</a>'
	html += '</center>'
	html += '</body>'
	return html

def gen_index_html(tables_list, market_data_fetch_interval):
	html = '<!DOCTYPE html>'
	html += '<html lang="en">'
	html += gen_html_head(market_data_fetch_interval)
	html += gen_html_body()
	html += '</html>'
	write_to_file(html, 'index.html')

if __name__ == '__main__':
	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)

	ticker_tables = os.getenv('TICKER_TABLES')
	if ticker_tables is None: bailmsg('Set TICKER_TABLES')

	market_data_fetch_interval = os.getenv('MARKET_DATA_FETCH_INTERVAL')
	if market_data_fetch_interval is None: market_data_fetch_interval = '4000'

	symb_list = []
	tables_list = ticker_tables.split(';')
	for tbl in tables_list:
		symbols = tbl.split('=')[1]
		symb_list += symbols.split(',')

	gen_index_html(tables_list, market_data_fetch_interval)
	time.sleep(2)
#	Sleep for a bit so supervisord knows all is well
