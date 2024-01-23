# ------------------------------------------------------------------------------
# Install build tools and compile the code
#FROM debian:bookworm-slim AS build
#ADD src /src
#WORKDIR /src
#RUN apt-get update && \
#	apt-get install -y build-essential \
#	  libmicrohttpd-dev libhiredis-dev && \
#	./compile.sh

# ------------------------------------------------------------------------------
# Pull base image
FROM redis:bookworm
MAINTAINER Brett Kuskie <fullaxx@gmail.com>

# ------------------------------------------------------------------------------
# Set environment variables
ENV DEBIAN_FRONTEND noninteractive

# ------------------------------------------------------------------------------
# Install software and clean up
COPY requirements.txt /install/
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
	  libmicrohttpd12 libhiredis0.14 supervisor python3-pip && \
	pip3 install --break-system-packages -r /install/requirements.txt && \
	apt-get clean && \
	rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/* && \
	mkdir /run/redis /var/log/redis && \
	chown redis:redis /run/redis /var/log/redis

# ------------------------------------------------------------------------------
# Prepare the image
COPY redis.conf /etc/redis/redis.conf
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY prices2redis.py /app/
#COPY --from=build /src/dashboard.exe /app/

# ------------------------------------------------------------------------------
# Expose ports
EXPOSE 80

# ------------------------------------------------------------------------------
# Define default command
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
