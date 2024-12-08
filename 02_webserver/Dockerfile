# ------------------------------------------------------------------------------
# Install build tools and compile the code
FROM fullaxx/ss_base_image AS build
ADD darkhttpd /dark
WORKDIR /dark
RUN apt-get update && \
	apt-get install -y build-essential && \
	gcc -Wall -O2 darkhttpd.c -o darkhttpd.exe && \
	strip darkhttpd.exe

# ------------------------------------------------------------------------------
# Pull base image
FROM fullaxx/ss_base_image
LABEL AUTHOR="Brett Kuskie <fullaxx@gmail.com>"

# ------------------------------------------------------------------------------
# Prepare the image
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY *.py /app/
COPY static/* /www/static/
COPY --from=build /dark/darkhttpd.exe /app/

# ------------------------------------------------------------------------------
# Expose ports
EXPOSE 80

# ------------------------------------------------------------------------------
# Define default command
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
