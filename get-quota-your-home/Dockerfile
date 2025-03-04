FROM ubuntu:24.04 AS base

RUN apt-get update > /dev/null && \
    apt-get install --yes python3 xfsprogs > /dev/null && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base AS dev
RUN apt-get update > /dev/null && \
    apt-get install --yes python3-pytest > /dev/null && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY dev-scripts/mount-xfs.sh /usr/local/bin/mount-xfs.sh
RUN chmod +x /usr/local/bin/mount-xfs.sh

COPY dev-scripts/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

COPY generate.py /usr/local/bin/generate.py

CMD ["/usr/local/bin/start.sh"]

# Production stage
FROM base AS prod
COPY generate.py /usr/local/bin/generate.py

CMD ["/usr/local/bin/generate.py"]
