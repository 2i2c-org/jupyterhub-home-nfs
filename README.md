# JupyterHub Home NFS

An NFS server for JupyterHub that runs within your Kubernetes cluster to provide persistent storage for users and a Python module to enforce storage quotas.

## Key Components

- [NFS Ganesha](https://github.com/nfs-ganesha/nfs-ganesha) is used as the NFS server
- [XFS](https://xfs.org/) as the filesystem
- [xfs_quota](https://man7.org/linux/man-pages/man8/xfs_quota.8.html) through [jupyterhub-home-nfs](https://github.com/2i2c-org/jupyterhub-home-nfs/tree/main/jupyterhub_home_nfs) is used to manage storage quotas

## Installation

JupyterHub Home NFS is installed as a Helm chart.

### Prerequisites

As a prerequisite, we need to create a volume in the cloud provider to store the home directories. Right now, we only support GKE, EKS and OpenStack. After the volume is created, we need to update the `values.yaml` file with the volume ID.

### Example configuration

Here's an example of a values.yaml file that can be used to install the Helm chart:

```yaml
gke:
  enabled: true
  volumeId: projects/example-project/zones/europe-west2-b/disks/hub-nfs-homedirs
quotaEnforcer:
  hardQuota: "1" # in GiB
```

Here we are using a GKE volume to store the home directories. We are also enabling the Prometheus exporter to collect disk usage metrics from the NFS server. And enforcing a hard quota of 1GiB per user.

### Installation through Helm

Once we have the values.yaml file, we can install the Helm chart using the following command:

```bash
helm upgrade --install --namespace jupyterhub-home-nfs --create-namespace jupyterhub-home-nfs oci://ghcr.io/2i2c-org/jupyterhub-home-nfs/jupyterhub-home-nfs --values values.yaml
```

Please refer to the [values.yaml](helm/jupyterhub-home-nfs/values.yaml) file for the complete list of configurable parameters.

### Using the NFS server in JupyterHub

Once the Helm chart is installed and running, please note the address of the NFS server. You can find the service IP using the command `kubectl get svc -n jupyterhub-home-nfs`, or use the full DNS name `home-nfs.jupyterhub-home-nfs.svc.cluster.local` (following the standard Kubernetes format: <service-name>.<namespace>.svc.cluster.local)

Once you have the address of the NFS server, you can use it to mount the home directories in your JupyterHub deployment using the example configuration in `examples/`.

First, we need to create a PersistentVolume and a PersistentVolumeClaim to mount the home directories using the NFS server created by JupyterHub Home NFS. To do this, replace the `server` field in the `nfs` section of the `PersistentVolume` with the address of the NFS server in [examples/jupyterhub-nfs-volume.yaml](examples/jupyterhub-nfs-volume.yaml).

```yaml
nfs:
  server: home-nfs.jupyterhub-home-nfs.svc.cluster.local
```

And then create the PersistentVolume and the PersistentVolumeClaim using the following command:

```bash
kubectl apply -f examples/jupyterhub-nfs-volume.yaml
```

Once the PersistentVolume and the PersistentVolumeClaim are created, you can use them to mount the home directories in your JupyterHub deployment. For example, we can use `examples/jupyterhub-values.yaml` to install JupyterHub with the home directories mounted using the NFS server created by JupyterHub Home NFS.

```bash
helm upgrade --cleanup-on-fail \
  --repo https://hub.jupyter.org/helm-chart/ \
  --install home-nfs-jupyterhub jupyterhub \
  --namespace jupyterhub-home-nfs \
  --values examples/jupyterhub-values.yaml
```

## Security

> [!WARNING]
> By default, the NFS server is accessible from within the cluster without any authentication. It is recommended to restrict access to the NFS server by enforcing Network Policies or enabling a client allow list to grant access only through kubelet and not from the pods directly.

### Network Policy Enforcement

Kubernetes Network Policies provide a way to control network traffic between pods and can be used to restrict direct access to the NFS server from user pods while allowing access from the kubelet.

By default, the JupyterHub helm chart blocks access to in-cluster services from single-user pods. So no additional Network Policies are needed to blocks access to the NFS server from the single-user pods of JupyterHub. But not all the cloud providers enforce Network Policies by default.

**Important considerations:**

- Network Policies require a CNI that supports them (such as Calico, Cilium, or Weave Net)
- The default CNI on some cloud providers like EKS for example do not enforce Network Policies by default.

The documentation of Zero to JupyterHub has a [relevant section](https://z2jh.jupyter.org/en/stable/administrator/security.html#kubernetes-network-policies) that can be used as a reference for blocking access to the NFS server from the single-user pods of JupyterHub.

### GKE Security Considerations

On GKE, Network Policies are enforced by default. So single-user pods are not allowed to access the NFS server directly and no additional action is needed to block access to the NFS server from the single-user pods of JupyterHub.

But for additional security, we can enable a client allow list in the NFS server configuration in the values.yaml file to grant access only from the IP range used by the kubelet agent on the nodes.

On GKE, the IP address used by the kubelet agent on the nodes is the first IP address in the node's podCIDR range. So for example, if the podCIDR range for a node is 10.120.2.0/24, the IP address used by the kubelet agent on the nodes is 10.120.2.1.

We need to find the podCIDR range for the nodes in the cluster. This can be done by running the following command:

```bash
kubectl get nodes -o jsonpath='{.items[*].spec.podCIDR}'
```

Once we have the podCIDR range for all the nodes, we can infer the allowedClients value from the podCIDR ranges. For example, if the podCIDR range for the nodes is 10.120.2.0/24, 10.120.3.0/24 and 10.120.4.0/24, the allowedClients value should be `10.120.*.1` where we use the `*` wildcard to account for all the nodes and the `.1` is the first IP address in the podCIDR range.

```yaml
nfsServer:
  enableClientAllowlist: true
  allowedClients:
    - "10.120.*.1"
```

### EKS Security Considerations

On EKS, the default CNI - Amazon VPC CNI, does not enforce Network Policies. And by default Amazon VPC CNI assigns IPs to pods from the same subnet as the nodes. So there is no way to define a separate CIDR block or pattern to allow access only from the kubelet using a client allow list.

**Network Policy Approach:**
Since Amazon VPC CNI [does not support enforcing Network Policies on the pods not managed by a deployment](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html#cni-network-policy-considerations), you need to use an alternative CNI like [Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks). Note that Calico can be configured to use Amazon VPC CNI as the underlying network provider and it can be configured to enforce Network Policies on the pods not managed by a deployment.

**IPTables Alternative:**
Alternatively, you can use iptables to restrict access to the NFS server. Here's an example of an init container that can be added to the pod definition to restrict access to the NFS server:

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

Once we have a shell into the container, we can run `python -m jupyterhub_home_nfs.generate` with the appropriate arguments to enforce storage quotas on the XFS filesystem.

### Running the tests

It's recommended to run the tests in the development container rather than your local machine.

You can run the tests with the following command:

```bash
docker compose --profile test up --build test
```

This will start the test container, mount a loopback device as an XFS filesystem and run the tests.
