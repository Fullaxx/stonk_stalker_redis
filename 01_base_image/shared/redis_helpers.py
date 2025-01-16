
import time
import redis

def is_market_open(r, interval):
	key = f'ALPACA:MARKET:STATUS:TEXT'
	market_status_text = r.get(key)
	while market_status_text is None:
		print('Waiting on {key} ...', flush=True)
		time.sleep(interval)
		market_status_text = r.get('ALPACA:MARKET:STATUS:TEXT')

	if (market_status_text == 'open'):
		is_market_open = True
	else:
		is_market_open = False

	return is_market_open

def wait_for_ready(r, key, interval):
	ready = r.exists(key)
	while not ready:
#		print('WAITING FOR READY ...', flush=True)
		time.sleep(interval)
		ready = r.exists(key)

def configure_redis(r, v):
#	https://stackoverflow.com/questions/67202021/whats-the-size-limitation-of-a-message-when-pub-sub-in-redis-channel
#	buffer_config = r.config_get('client-output-buffer-limit')
#	print(buffer_config)

	if (v): print('CONFIG SET notify-keyspace-events AKE: ', end='')
	try:
		success = r.config_set('notify-keyspace-events', 'AKE')
	except redis.exceptions.ResponseError as e:
		if (v): print('FAILED!', flush=True)
		return False
	else:
		if (v): print('SUCCESS', flush=True)
		return True

def ping_redis(r):
	try:
		connected = r.ping()
	except redis.exceptions.ConnectionError as e:
		print('r.ping() failed:', e, flush=True)
		connected = False
	return connected

def connect_to_redis(redis_url, decode_all_responses, verbose, debug_python):
	if debug_python: print('REDIS_URL:', redis_url, flush=True)
	r = redis.Redis.from_url(redis_url, decode_responses=decode_all_responses)

	connected = ping_redis(r)
	while not connected:
		time.sleep(0.1)
		connected = ping_redis(r)

	if (verbose): print('Connected to redis @', redis_url, flush=True)

#	This isnt always necessary for functionality
#	but we use it to make sure the server is fully loaded and ready
	success = configure_redis(r, verbose)
	while not success:
		time.sleep(0.1)
		success = configure_redis(r, verbose)

	return r
