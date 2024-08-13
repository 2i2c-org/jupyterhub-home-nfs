# Jupyter Home NFS

An NFS server for JupyterHub that runs within your Kubernetes cluster to provide persistent storage for users and enforce storage quotas.

## Key Components
- [NFS Ganesha]([https://](https://github.com/nfs-ganesha/nfs-ganesha) is used as the NFS server
- [XFS]([https://](https://xfs.org/)) as the filesystem
- [xfs_quota]([\[https://\](https://linux.die.net](https://man7.org/linux/man-pages/man8/xfs_quota.8.html) through [get-quota-your-home](https://github.com/yuvipanda/get-quota-your-home) is used to manage storage quotas