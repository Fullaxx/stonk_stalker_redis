# ------------------------------------------------------------------------------
# Install build tools and compile the code
FROM debian:bookworm-slim AS build
ADD darkhttpd /dark
WORKDIR /dark
RUN apt-get update && \
	apt-get install -y build-essential && \
	gcc -Wall -O2 darkhttpd.c -o darkhttpd.exe && \
	strip darkhttpd.exe

# ------------------------------------------------------------------------------
# Pull base image
FROM redis:bookworm
LABEL AUTHOR="Brett Kuskie <fullaxx@gmail.com>"

# ------------------------------------------------------------------------------
# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=US/Eastern

# ------------------------------------------------------------------------------
# Install software and clean up
COPY requirements.txt /install/
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
	  libmicrohttpd12 libhiredis0.14 supervisor python3-pip && \
	pip3 install --break-system-packages -r /install/requirements.txt && \
	apt-get clean && \
	rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/* && \
	mkdir /run/redis /var/log/redis /www && \
	chown redis:redis /run/redis /var/log/redis /www

# ------------------------------------------------------------------------------
# Prepare the image
COPY redis.conf /etc/redis/redis.conf
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY yf_update_info.py redis_helpers.py yfTickerInfo2Redis.py create_marketdb.py /app/
#COPY prices2redis.py bars2redis.py get_market_data.py /app/
COPY --from=build /dark/darkhttpd.exe /app/

# ------------------------------------------------------------------------------
# Expose ports
EXPOSE 80

# ------------------------------------------------------------------------------
# Define default command
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
