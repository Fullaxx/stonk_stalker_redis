#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path
#from pprint import pprint

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

if __name__ == '__main__':
	cfg_dir = Path('/config')
	if not cfg_dir.is_dir():
		bailmsg(f'/config is not a directory!')
	cfg_file = Path('/config/tables.json')
	if not cfg_file.is_file():
		bailmsg(f'/config/tables.json is not a file!')

	with open('/config/tables.json', 'r') as f:
		config_str = f.read()
		config = json.loads(config_str)
#		pprint(config)
		for k,v in config.items():
			print(k, v['table_name'], v['symbols'])
