#!/usr/bin/env python3
# pip3 install redis

import os
import redis

if __name__ == '__main__':
	r = redis.from_url(os.getenv('REDISURL'))
	print('MARKET:PRICES:', r.get('MARKET:PRICES'))
