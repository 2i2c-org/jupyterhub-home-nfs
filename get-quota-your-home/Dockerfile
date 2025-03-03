# Let's try to match the environment the NFS Server is running on
# So the version of xfs_quota used matches the server's
FROM ubuntu:22.04 as base

RUN apt-get update > /dev/null && \
    apt-get install --yes python3 xfsprogs > /dev/null && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as dev
RUN apt-get update > /dev/null && \
    apt-get install --yes python3-pip > /dev/null && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip3 install pytest

COPY scripts/mount-xfs.sh /usr/local/bin/mount-xfs.sh
RUN chmod +x /usr/local/bin/mount-xfs.sh

COPY scripts/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

COPY generate.py /usr/local/bin/generate.py

CMD ["/usr/local/bin/start.sh"]

# Production stage
FROM base as prod
COPY generate.py /usr/local/bin/generate.py

CMD ["/usr/local/bin/generate.py"]