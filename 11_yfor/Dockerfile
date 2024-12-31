# ------------------------------------------------------------------------------
# Pull base image
FROM fullaxx/ss_base_image
LABEL author="Brett Kuskie <fullaxx@gmail.com>"

# ------------------------------------------------------------------------------
# Prepare the image
#COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY *.py /app/

# ------------------------------------------------------------------------------
# Expose ports
EXPOSE 7982

# ------------------------------------------------------------------------------
# Define default command
#CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
CMD ["/app/octopus_receptor.py"]
