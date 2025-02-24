# Let's try to match the environment the NFS Server is running on
# So the version of xfs_quota used matches the server's
FROM ubuntu:22.04

RUN apt-get update > /dev/null && \
    apt-get install --yes python3 python3-pip xfsprogs > /dev/null && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./setup.py /opt/jupyterhub-home-nfs/setup.py
COPY ./jupyterhub_home_nfs /opt/jupyterhub-home-nfs/jupyterhub_home_nfs

WORKDIR /opt/jupyterhub-home-nfs

RUN pip3 install -e .

CMD ["python3", "-m", "jupyterhub_home_nfs.generate"]
