#!/usr/bin/env python3

import os
import sys
import redis

#from argparse import ArgumentParser

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False
g_dailystats2redis_set_key = 'YFINANCE:LAUNCHER:DAILYSTATS2REDIS:SET'

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

# Acquire the complete list of tables from redis
# Reload stack at g_dailystats2redis_set_key to a set of all tables
def reload_dailystats2redis():
	searchpattern = f'DASHBOARD:TABLES:*'
	tables_list = sorted(g_rc.scan_iter(searchpattern))
	num_updated = g_rc.sadd(g_dailystats2redis_set_key, *tables_list)
	print(f'{g_dailystats2redis_set_key} RELOADED: {num_updated} added', flush=True)

def pop_random_table():
	random_table = g_rc.spop(g_dailystats2redis_set_key)
	while (random_table is None):
		reload_dailystats2redis()
		random_table = g_rc.spop(g_dailystats2redis_set_key)
	return random_table

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
#	parser = ArgumentParser()
#	parser.add_argument('--reload', '-r', required=False, action='store_true')
#	parser.add_argument('--pop', '-p', required=False, action='store_true')
#	args = parser.parse_args()

	redis_url = acquire_environment()
	g_rc = connect_to_redis(redis_url, True, False, g_debug_python)
	wait_for_ready(g_rc, 'DASHBOARD:READY', 0.1)

	table = pop_random_table()
	os.system(f'./dailystats2redis.py -k {table}')
#	sys.exit(0)

#	if args.reset:
#		reload_dailystats2redis()
#
#	if args.pop:
#		t = pop_random_table()
#		if (t is not None): print(t)
