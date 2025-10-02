# Changelog

## [1.1.1] - 2025-10-02

([full changelog](https://github.com/2i2c-org/jupyterhub-home-nfs/compare/1.1.0...34c00b79a00c146f2d19fd4b0aa4481863d9beb9))

### Enhancements made

- Mkdir and chown unconditionally and let it throw errors if it fails [#56](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/56) ([@GeorgianaElena](https://github.com/GeorgianaElena))
- Setup a custom ownership uid:gid of the initial share  [#55](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/55) ([@GeorgianaElena](https://github.com/GeorgianaElena), [@yuvipanda](https://github.com/yuvipanda))

### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/2i2c-org/jupyterhub-home-nfs/graphs/contributors?from=2025-09-25&to=2025-10-02&type=c))

@GeorgianaElena ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3AGeorgianaElena+updated%3A2025-09-25..2025-10-02&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3Ayuvipanda+updated%3A2025-09-25..2025-10-02&type=Issues))

## [1.1.0] - 2025-09-25

([full changelog](https://github.com/2i2c-org/jupyterhub-home-nfs/compare/1.0.1...fa9a311996bb532748d6d650644e2ccb45e92724))

### Enhancements made

- feat: don't invalidate quotas [#54](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/54) ([@agoose77](https://github.com/agoose77))
- feat: pass through file paths [#53](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/53) ([@agoose77](https://github.com/agoose77))
- feat: refactoring and improved logging [#50](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/50) ([@agoose77](https://github.com/agoose77))
- feat: Improved logging and refactoring [#49](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/49) ([@agoose77](https://github.com/agoose77), [@sunu](https://github.com/sunu))
- Squash all users to one particular uid and gid [#48](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/48) ([@GeorgianaElena](https://github.com/GeorgianaElena), [@yuvipanda](https://github.com/yuvipanda))
- Handle xfs_quota failing more gracefully [#44](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/44) ([@yuvipanda](https://github.com/yuvipanda))
- Set uid and gid [#42](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/42) ([@GeorgianaElena](https://github.com/GeorgianaElena))

### Bugs fixed

- feat: increase filesystem reconciliation granularity [#52](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/52) ([@agoose77](https://github.com/agoose77), [@sunu](https://github.com/sunu))
- fix: clear existing quotas on startup [#51](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/51) ([@agoose77](https://github.com/agoose77))
- Set PYTHONUNBUFFERED=1 for enforce-xfs-quotas [#43](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/43) ([@yuvipanda](https://github.com/yuvipanda))

### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/2i2c-org/jupyterhub-home-nfs/graphs/contributors?from=2025-08-26&to=2025-09-25&type=c))

@agoose77 ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3Aagoose77+updated%3A2025-08-26..2025-09-25&type=Issues)) | @GeorgianaElena ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3AGeorgianaElena+updated%3A2025-08-26..2025-09-25&type=Issues)) | @sunu ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3Asunu+updated%3A2025-08-26..2025-09-25&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3Ayuvipanda+updated%3A2025-08-26..2025-09-25&type=Issues))

## [1.0.1] - 2025-08-26

([full changelog](https://github.com/2i2c-org/jupyterhub-home-nfs/compare/1.0.0...03c5049dc74cd6be237897c333ba909e869afeeb))

## Bugs fixed

- PV name must be unique [#38](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/38) ([@GeorgianaElena](https://github.com/GeorgianaElena), [@sunu](https://github.com/sunu))

## Maintenance

- Setup a baseVersion in chartpress and update release instructions [#39](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/39) ([@GeorgianaElena](https://github.com/GeorgianaElena))

## Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/2i2c-org/jupyterhub-home-nfs/graphs/contributors?from=2025-08-22&to=2025-08-26&type=c))

@GeorgianaElena ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3AGeorgianaElena+updated%3A2025-08-22..2025-08-26&type=Issues)) | @sunu ([activity](https://github.com/search?q=repo%3A2i2c-org%2Fjupyterhub-home-nfs+involves%3Asunu+updated%3A2025-08-22..2025-08-26&type=Issues))

## [1.0.0] - 2025-08-22

### Breaking Changes

- **BREAKING**: Switched to predictable resource naming following the z2jh pattern, borrowed from binderhub-service. Resources now append `-home-nfs` to the fullname base. When `fullnameOverride` is an empty string `""` (the default), resources are named `home-nfs` (e.g., `home-nfs` service). When `fullnameOverride` is set to a custom value like `"myjupyterhub"`, resources are named `myjupyterhub-home-nfs` (e.g., `myjupyterhub-home-nfs` service). This is a breaking change from the previous release-name based pattern. Fixes [#30](https://github.com/2i2c-org/jupyterhub-home-nfs/issues/30).

### Enhancements

- Automatically resize the filesystem if necessary [#37](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/37) ([@yuvipanda](https://github.com/yuvipanda), [@GeorgianaElena](https://github.com/GeorgianaElena))

- Added quota override functionality for specific folders. This allows setting custom quotas for individual folders, which is particularly useful for shared folders that may need different quota limits than regular user directories. The feature is configured via the `quota_overrides` option which maps folder names to custom quota values in GB [#36](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/36) ([@sunu](https://github.com/sunu), [@GeorgianaElena](https://github.com/GeorgianaElena))

  ```yaml
  quotaEnforcer:
    config:
      QuotaManager:
        quota_overrides:
          "_shared-public": 50 # Custom quota of 50 GB for the shared public folder
  ```

- Fix FileNotFoundError when export directory doesn't exist [#35](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/35) ([@sunu](https://github.com/sunu), [@GeorgianaElena](https://github.com/GeorgianaElena))

- Added standard Helm labels (`app.kubernetes.io/name`, `app.kubernetes.io/instance`, `app.kubernetes.io/version`, `app.kubernetes.io/managed-by`, `helm.sh/chart`) to all Kubernetes resources for better resource management and monitoring [#34](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/34) ([@sunu](https://github.com/sunu), [@GeorgianaElena](https://github.com/GeorgianaElena), [@yuvipanda](https://github.com/yuvipanda))

- Change how version is parsed, move from `set-output` to use `$GITHUB_ENV`, skip publish for certain commits [#32](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/32) ([@shaneknapp](https://github.com/shaneknapp), [@sunu](https://github.com/sunu))

- Add a changelog file to keep track of changes [#27](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/27) ([@sunu](https://github.com/sunu), [@sgibson91](https://github.com/sgibson91))

- Optional feature to allow connections from allowed IPs only; and improved documentation for installation and security [#25](https://github.com/2i2c-org/jupyterhub-home-nfs/pull/25) ([@sunu](https://github.com/sunu), [@GeorgianaElena](https://github.com/GeorgianaElena), [@yuvipanda](https://github.com/yuvipanda))

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
