FROM debian:bullseye-slim

# Don't buffer stdout and stderr as it breaks realtime logging
ENV PYTHONUNBUFFERED 1

# Create an unprivileged user to run the application process
ENV ZENITH_UID 1001
ENV ZENITH_USER zenith
RUN useradd \
      --no-create-home \
      --user-group \
      --shell /sbin/nologin \
      --uid $ZENITH_UID \
      $ZENITH_USER

# Install tini, which we will use to marshal the processes and Python
RUN apt-get update && \
    apt-get install -y git python3 python3-pip tini && \
    rm -rf /var/lib/apt/lists/*

# Installing dependencies separately ensures better use of the build cache
COPY requirements.txt /opt/zenith/sync/
RUN pip3 install --no-deps --requirement /opt/zenith/sync/requirements.txt

COPY . /opt/zenith/sync
RUN pip3 install --no-deps -e /opt/zenith/sync

USER $ZENITH_UID
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["zenith-sync"]