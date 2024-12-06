
import json
from pathlib import Path

def read_ss_config():
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
