# Changelog

## [Unreleased]

Future changes that are not yet released.

## v0.2.0 - 2025-04-21

### Breaking Changes

- Configuration and command-line arguments are now managed using [traitlets](https://traitlets.readthedocs.io/en/stable/), providing type validation and aligning with patterns used across the JupyterHub ecosystem. This introduces a breaking change in how Helm values are passed. Part of [PR #22](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/22).

  For example, the path, hard quota limits etc are now passed in `quotaEnforcer.config.QuotaManager` instead of directly under `quotaEnforcer`. For example:

  ```yaml
  quotaEnforcer:
    config:
      QuotaManager:
        paths: ["/export"]
        hard_quota: 10
  ```

- As part of [PR #22](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/22), the default persistent volume size label was updated from 10Gi to 1M to clarify that it's a placeholder and not the actual disk size.
  For existing deployments, if the size was previously unset, it must now be explicitly set to the current value (e.g. `10Gi`) under the `persistentVolume` section like this:

  ```yaml
  persistentVolume:
    size: 10Gi
  ```

  This avoids Kubernetes errors due to the perceived size reduction from 10Gi to 1M.

### Enhancements

- Added an option to disable quota enforcement. Part of [PR #22](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/22).
- Added the option to exclude certain directories from quota enforcement as part of [PR #19](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/19) and [PR #20](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/20).
- Storage quota enforcement functionality is now packaged as a python package named `jupyterhub_home_nfs`. Part of [PR #17](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/17).
- Added end-to-end tests for quota enforcement in [PR #21](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/21)
- Added `values.schema.json` for linting helm values. Part of [PR #22](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/22)
- Added pre-commit hooks to check linting and formatting in [PR #23](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/23)

### Documentation

- Added documentation on how to make a new release. Part of [PR #22](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/22).

## Older releases

Please use `git log` to get the details of the changes in the older releases.
