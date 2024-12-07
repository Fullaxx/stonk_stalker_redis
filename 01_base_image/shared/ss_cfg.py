
import json
from pathlib import Path

def read_ss_config():
	cfg_dir = Path('/config')
	if not cfg_dir.is_dir():
		bailmsg(f'/config is not a directory!')
	cfg_file = Path('/config/dashboard_config.json')
	if not cfg_file.is_file():
		bailmsg(f'/config/dashboard_config.json is not a file!')

	with open('/config/dashboard_config.json', 'r') as f:
		config_str = f.read()
		config = json.loads(config_str)

	if 'DASHBOARD_CONFIG' not in config:
		config['DASHBOARD_CONFIG'] = {
			'DISPLAY_MARKET_CAP' : False,
			'DISPLAY_FPE_RATIO' : False,
			'DISPLAY_PST12_RATIO' : False,
			'DISPLAY_PEG_RATIO' : False,
			'DISPLAY_PB_RATIO' : False,
			'DISPLAY_OTHER_URLS' : False,
		}

	return config
