# Jupyter Home NFS

An NFS server for JupyterHub that runs within your Kubernetes cluster to provide persistent storage for users and enforce storage quotas.

## Key Components
- [NFS Ganesha](https://github.com/nfs-ganesha/nfs-ganesha) is used as the NFS server
- [XFS](https://xfs.org/) as the filesystem
- [xfs_quota](https://man7.org/linux/man-pages/man8/xfs_quota.8.html) through [jupyterhub-home-nfs](https://github.com/2i2c-org/jupyterhub-home-nfs/tree/main/jupyterhub_home_nfs) is used to manage storage quotas
