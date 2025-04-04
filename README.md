# JupyterHub Home NFS

An NFS server for JupyterHub that runs within your Kubernetes cluster to provide persistent storage for users and a Python module to enforce storage quotas.

## Key Components

- [NFS Ganesha](https://github.com/nfs-ganesha/nfs-ganesha) is used as the NFS server
- [XFS](https://xfs.org/) as the filesystem
- [xfs_quota](https://man7.org/linux/man-pages/man8/xfs_quota.8.html) through [jupyterhub-home-nfs](https://github.com/2i2c-org/jupyterhub-home-nfs/tree/main/jupyterhub_home_nfs) is used to manage storage quotas

## Installation

JupyterHub Home NFS is installed as a Helm chart.

```bash
helm install jupyterhub-home-nfs oci://ghcr.io/2i2c-org/jupyterhub-home-nfs/jupyterhub-home-nfs --values values.yaml
```

## Security

> [!WARNING]  
> By default, the NFS server is accessible from within the cluster without any authentication. It is recommended to restrict access to the NFS server by enforcing Network Policies or enabling client whitelisting to allow access only through kubelet and not from the pods directly.
### GKE

On GKE, this can be done by enabling client whitelisting in the values.yaml file and allowing access only from the IP range used by the kubelet agent on the nodes.

On GKE, the IP address used by the kubelet agent on the nodes is the first IP address in the node's podCIDR range. So for example, if the podCIDR range for a node is 10.120.2.0/24, the IP address used by the kubelet agent on the nodes is 10.120.2.1.

We need to find the podCIDR range for the nodes in the cluster. This can be done by running the following command:

```bash
kubectl get nodes -o jsonpath='{.items[*].spec.podCIDR}'
```

Once we have the podCIDR range for all the nodes, we can infer the allowedClients value from the podCIDR ranges. For example, if the podCIDR range for the nodes is 10.120.2.0/24, 10.120.3.0/24 and 10.120.4.0/24, the allowedClients value should be 10.120.*.1 where we use the * wildcard to account for all the nodes and the .1 is the first IP address in the podCIDR range.

```yaml
nfsServer:
  enableClientWhitelist: true
  allowedClients:
    - "10.120.*.1"
```

Additionally, we can use Kubernetes Network Policies to block direct access to the NFS server from the pods. The documentation of Zero to JupyterHub has a [relevant section](https://z2jh.jupyter.org/en/stable/administrator/security.html#kubernetes-network-policies) that can be used as a reference for blocking access to the NFS server from the single-user pods of JupyterHub.


### EKS

On EKS, by default Amazon VPC CNI assigns IPs to pods from the same subnet as the nodes. So there is no way to define a separate CIDR block or pattern to allow access only from the kubelet.

One way to restrict access to the NFS server is to use a Network Policy to allow access only from the pods that need access to the NFS server. But since Amazon VPC CNI [does not support enforcing Network Policies on the pods not managed by a deployment](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html#cni-network-policy-considerations), we need to make sure we use an alternative to Amazon VPC CNI like [Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks). Note that Calico can be configured to use Amazon VPC CNI as the underlying network provider.

The documentation of Zero to JupyterHub has a [relevant section](https://z2jh.jupyter.org/en/stable/administrator/security.html#kubernetes-network-policies) that can be used as a reference for blocking access to the NFS server from the single-user pods of JupyterHub.

Alternatively, we can use IP tables to restrict access to the NFS server. Here's an example of an init container that can be added to the pod definition to restrict access to the NFS server:

```yaml
initContainers:
  - name: block-nfs-access
  command:
      - /bin/sh
      - -c
      - |
      iptables --append OUTPUT --protocol tcp --destination-port 2049 --jump DROP \
      && iptables --append OUTPUT --protocol tcp --destination-port 20048 --jump DROP \
      && iptables --append OUTPUT --protocol tcp --destination-port 111 --jump DROP \
      && iptables --append OUTPUT --protocol udp --destination-port 2049 --jump DROP \
      && iptables --append OUTPUT --protocol udp --destination-port 20048 --jump DROP \
      && iptables --append OUTPUT --protocol udp --destination-port 111 --jump DROP
  image: quay.io/jupyterhub/k8s-network-tools:4.1.0
  securityContext:
      capabilities:
      add:
          - NET_ADMIN
      privileged: true
      runAsUser: 0
```

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
