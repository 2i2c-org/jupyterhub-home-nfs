FROM ubuntu:24.04 AS base

RUN apt-get update > /dev/null && \
    apt-get install --yes python3 python3-pip python3-venv xfsprogs > /dev/null && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY ./setup.py /opt/jupyterhub-home-nfs/setup.py
COPY ./README.md /opt/jupyterhub-home-nfs/README.md

WORKDIR /opt/jupyterhub-home-nfs

# Development stage
FROM base AS dev

COPY dev-scripts/mount-xfs.sh /usr/local/bin/mount-xfs.sh
RUN chmod +x /usr/local/bin/mount-xfs.sh

COPY dev-scripts/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

RUN pip install pytest

COPY ./jupyterhub_home_nfs /opt/jupyterhub-home-nfs/jupyterhub_home_nfs

RUN pip install -e .

CMD ["/usr/local/bin/start.sh"]

# Production stage
FROM base AS prod

COPY ./jupyterhub_home_nfs /opt/jupyterhub-home-nfs/jupyterhub_home_nfs

RUN pip install -e .

CMD ["python", "-m", "jupyterhub_home_nfs.generate"]
