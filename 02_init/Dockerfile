# ------------------------------------------------------------------------------
# Pull base image
FROM fullaxx/ss_base_image
LABEL author="Brett Kuskie <fullaxx@gmail.com>"

# ------------------------------------------------------------------------------
# Prepare the image
COPY *.py /app/

# ------------------------------------------------------------------------------
# Define healthcheck
# HEALTHCHECK --interval=2s --timeout=5s \
# CMD /app/healthcheck.py

# ------------------------------------------------------------------------------
# Define default command
CMD ["/app/publish_config.py"]
