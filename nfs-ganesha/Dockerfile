FROM debian:forky AS build

# Rebuild nfs-ganesha with QOS enabled
RUN DEBIAN_FRONTEND=noninteractive \
    && sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get build-dep -y nfs-ganesha \
    && apt-get source nfs-ganesha \
    && cd nfs-ganesha-*/ \
    && sed -i '/-DUSE_FSAL_XFS=NO \\/ a\             -DENABLE_QOS=YES \\'  debian/rules \
    && dpkg-buildpackage -rfakeroot

# Consume build package
FROM debian:forky
COPY --from=build nfs-ganesha*_amd64.deb /

# Install nfs-ganesha from official PPA & some useful tools
# duc: Disk Usage Analyzer (https://duc.zevv.nl/)
# git, less, rsync, screen, tree, vim: common utilities for development and debugging
RUN DEBIAN_FRONTEND=noninteractive \
    && ls \
    && apt-get update \
    && apt-get install -y \
      netbase nfs-common dbus /nfs-ganesha_*_amd64.deb /nfs-ganesha-vfs_*_amd64.deb\
        duc git less rsync screen tree vim \
    && rm /nfs-ganesha*_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && mkdir -p /run/rpcbind /export /var/run/dbus \
    && touch /run/rpcbind/rpcbind.xdr /run/rpcbind/portmap.xdr \
    && chmod 755 /run/rpcbind/* \
    && chown messagebus:messagebus /var/run/dbus

# Add startup script
COPY --chmod=0755 start.sh /

# NFS ports and portmapper
EXPOSE 2049 38465-38467 662 111/udp 111

# Start Ganesha NFS daemon by default
CMD ["/start.sh"]
