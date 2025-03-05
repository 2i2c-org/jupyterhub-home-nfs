# Jupyter Home NFS

An NFS server for JupyterHub that runs within your Kubernetes cluster to provide persistent storage for users and enforce storage quotas.

## Key Components
- [NFS Ganesha](https://github.com/nfs-ganesha/nfs-ganesha) is used as the NFS server
- [XFS](https://xfs.org/) as the filesystem
- [xfs_quota](https://man7.org/linux/man-pages/man8/xfs_quota.8.html) through [jupyterhub-home-nfs](https://github.com/2i2c-org/jupyterhub-home-nfs/tree/main/jupyterhub_home_nfs) is used to manage storage quotas

## Development

### Prerequisites

- Docker
- Docker Compose

> [!NOTE]
> On Mac, Docker Desktop might not support mounting loopback devices as XFS filesystems. If you are on Mac, consider using an alternative implementation like [colima](https://github.com/abiosoft/colima).

### Developing locally

For development, we use a loopback device and mount it as an XFS filesystem inside the container.

Run the following command to start the development container:

```bash
docker compose up --build app
```

This will start the development container, mount a loopback device as an XFS filesystem at `/mnt/docker-test-xfs`.

Once the container is running, we can run the following command to get a shell into the container:

```bash
docker compose exec -it app bash
```

Once we have a shell into the container, we can run `/usr/local/bin/generate.py` with the appropriate arguments to enforce storage quotas on the XFS filesystem.

### Running the tests

It's recommended to run the tests in the development container rather than your local machine.

You can run the tests with the following command:

```bash
docker compose --profile test up --build test
```

This will start the test container, mount a loopback device as an XFS filesystem and run the tests.
