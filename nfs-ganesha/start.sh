#!/bin/bash
set -e

function init_rpc {
	echo "Starting rpcbind"
	rpcbind || return 0
	rpc.statd -L || return 0
	rpc.idmapd || return 0
	sleep 1
}

function init_dbus {
	echo "Starting dbus"
	rm -f /var/run/dbus/system_bus_socket
	rm -f /var/run/dbus/pid
	dbus-uuidgen --ensure
	dbus-daemon --system --fork
	sleep 1
}

init_rpc
init_dbus


echo "Starting Ganesha NFS"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib
# Ensure the Ganesha directories exist and have correct permissions
mkdir -p /var/run/ganesha /var/lib/nfs/ganesha /export
chown -R nobody:nogroup /var/run/ganesha /var/lib/nfs/ganesha /export /etc/ganesha
# Start Ganesha with debugging enabled
exec /usr/bin/ganesha.nfsd -F -L /dev/stdout -f /etc/ganesha/ganesha.conf -N NIV_EVENT