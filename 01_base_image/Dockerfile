# ------------------------------------------------------------------------------
# Pull base image
FROM ubuntu:jammy
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
	  curl htop lsof nano tree vim-tiny \
	  libmicrohttpd12 libhiredis0.14 supervisor python3-pip && \
	pip3 install -r /install/requirements.txt && \
	apt-get clean && \
	rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/*

# ------------------------------------------------------------------------------
# Prepare the image
COPY shared/*.py /app/
