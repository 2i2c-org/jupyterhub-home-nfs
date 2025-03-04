#!/bin/bash
set -e

FILE_SIZE="301M" # 300MB is the minimum size for xfs
MOUNT_POINT="/mnt/docker-test-xfs"
BACKING_FILE="/tmp/xfs.${FILE_SIZE}"

# Create the mount point
mkdir -p ${MOUNT_POINT}

# Delete the backing file if it exists
rm -f ${BACKING_FILE}

# Create the backing file
dd if=/dev/zero of=${BACKING_FILE} bs=1 count=0 seek=${FILE_SIZE}

# Format the file to xfs
mkfs -t xfs -q ${BACKING_FILE}

# Mount the file to the mount point; use pquota to enable project quotas
mount -o loop,rw ${BACKING_FILE} -o pquota ${MOUNT_POINT}
