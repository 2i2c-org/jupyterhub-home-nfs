# How to make a release

We publish Docker images and Helm charts to GitHub Container Registry (ghcr.io) for every tag. This document describes how to make a new version tag and push it to GitHub.

## Version Updates

To update the version:

1. **Prepare Your Environment**

   Ensure your local repository is up-to-date and install required tools:

    ```bash
    git checkout main
    git fetch origin main
    git reset --hard origin/main
    ```

    Install tbump if not already installed:

    ```bash
    pip install tbump
    ```

2. **Update Version with tbump**

   Use tbump to update the version numbers in the codebase:

   First, run a dry run to see what will change:

   ```bash
   tbump --dry-run X.Y.Z
   ```

   Then, run the actual update:

   ```bash
   tbump X.Y.Z
   ```

   This will:
   - Update `__version__` in `jupyterhub_home_nfs/__init__.py`
   - Update version and appVersion in `helm/jupyterhub-home-nfs/Chart.yaml`
   - Create a git commit
   - Create a git tag

3. **Push Changes**

   Push the changes and tag to GitHub:

   ```bash
   git push origin main
   git push origin X.Y.Z
   ```

4. **CI Automation**

   Once we create a tag, the GitHub Actions workflow ([`build-publish-docker-helm.yaml`](https://github.com/2i2c-org/jupyterhub-home-nfs/blob/main/.github/workflows/build-publish-docker-helm.yaml)) will automatically:
   
   - Build the Docker images
   - Push them to GitHub Container Registry (ghcr.io)
   - Update the Helm chart with the new image tags
   - Package and publish the Helm chart to ghcr.io

## Verification

After pushing your changes:

1. Check the GitHub Actions [workflow status](https://github.com/2i2c-org/jupyterhub-home-nfs/actions)
2. Verify that:
   - The workflow completed successfully
   - The Docker images are available [on ghcr.io](https://github.com/orgs/2i2c-org/packages?repo_name=jupyterhub-home-nfs)
   - The Helm chart is published to [ghcr.io](https://github.com/2i2c-org/jupyterhub-home-nfs/pkgs/container/jupyterhub-home-nfs%2Fjupyterhub-home-nfs)
