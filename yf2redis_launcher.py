#!/usr/bin/env python3

import os
import sys
import json
import time
from pathlib import Path

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def read_tables_config():
	cfg_dir = Path('/config')
	if not cfg_dir.is_dir():
		bailmsg(f'/config is not a directory!')
	cfg_file = Path('/config/tables.json')
	if not cfg_file.is_file():
		bailmsg(f'/config/tables.json is not a file!')

	with open('/config/tables.json', 'r') as f:
		config_str = f.read()
		config = json.loads(config_str)

	return config

if __name__ == '__main__':
	ri_str = os.getenv('YF_REQUEST_INTERVAL')
	request_interval = 30 if ri_str is None else int(ri_str)

	symbols_list = []
	tables_config = read_tables_config()
	for k,v in tables_config.items():
		symbols_str = v['symbols']
		symbols_list += symbols_str.split(',')

#	When this loop is done, it will exit 0
#	Current Design: supervisord will restart it automatically
	for symbol in symbols_list:
		os.system(f'/app/yf2redis.py -s {symbol}')
		time.sleep(request_interval)
