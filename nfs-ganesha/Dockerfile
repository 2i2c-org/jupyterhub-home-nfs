FROM ubuntu:22.04

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y software-properties-common \
    && add-apt-repository ppa:nfs-ganesha/nfs-ganesha-5 \
    && add-apt-repository ppa:nfs-ganesha/libntirpc-5 \
    && apt-get update \
    && apt-get install -y netbase nfs-common dbus nfs-ganesha nfs-ganesha-vfs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && mkdir -p /run/rpcbind /export /var/run/dbus \
    && touch /run/rpcbind/rpcbind.xdr /run/rpcbind/portmap.xdr \
    && chmod 755 /run/rpcbind/* \
    && chown messagebus:messagebus /var/run/dbus

# Add startup script
COPY --chmod=0755 start.sh /

COPY ganesha.conf /etc/ganesha/ganesha.conf

# NFS ports and portmapper
EXPOSE 2049 38465-38467 662 111/udp 111

# Start Ganesha NFS daemon by default
CMD ["/start.sh"]