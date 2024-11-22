
import time
import redis

def configure_redis(r):
#	https://stackoverflow.com/questions/67202021/whats-the-size-limitation-of-a-message-when-pub-sub-in-redis-channel
#	buffer_config = r.config_get('client-output-buffer-limit')
#	print(buffer_config)

	print('CONFIG SET notify-keyspace-events AKE: ', end='')
	try:
		success = r.config_set('notify-keyspace-events', 'AKE')
	except redis.exceptions.ResponseError as e:
		print('FAILED!', flush=True)
		return False
	else:
		print('SUCCESS', flush=True)
		return True

def ping_redis(r):
	try:
		connected = r.ping()
	except redis.exceptions.ConnectionError as e:
		print('r.ping() failed:', e, flush=True)
		connected = False
	return connected

def connect_to_redis(redis_url, decode_all_responses, debug_python):
	if debug_python: print('REDIS_URL:', redis_url, flush=True)
	r = redis.Redis.from_url(redis_url, decode_responses=decode_all_responses)

	connected = ping_redis(r)
	while not connected:
		time.sleep(0.1)
		connected = ping_redis(r)

	print('Connected to redis @', redis_url, flush=True)

#	This isnt always necessary for functionality
#	but we use it to make sure the server is fully loaded and ready
	success = configure_redis(r)
	while not success:
		time.sleep(0.1)
		success = configure_redis(r)

	return r
