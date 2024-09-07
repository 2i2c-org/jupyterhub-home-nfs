# Let's try to match the environment the NFS Server is running on
# So the version of xfs_quota used matches the server's
FROM ubuntu:22.04

RUN apt-get update > /dev/null && \
    apt-get install --yes python3 xfsprogs > /dev/null && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY generate.py /usr/local/bin/generate.py

CMD ["/usr/local/bin/generate.py"]