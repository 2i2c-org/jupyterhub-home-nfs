import os
import subprocess
import tempfile
import textwrap
from pprint import pprint  # noqa: F401

import pytest
from prometheus_client.core import Sample

from jupyterhub_home_nfs import metrics
from jupyterhub_home_nfs.generate import OWNERSHIP_PREAMBLE, QuotaManager

MOUNT_POINT = "/mnt/docker-test-xfs"


GIB_TO_KIB = 1024 * 1024
# When setting limits, the value is compressed into the appropriate block number
# By default, blocks are 4 KiB wide.
DEFAULT_BLOCK_SIZE_KIB = 4


@pytest.fixture(autouse=True)
def cleanup_traitlet_singleton():
    yield
    QuotaManager.clear_instance()


# This is the mount point defined in mount-xfs.sh
# It is named docker-test-xfs to avoid conflicts with the host's mount point
# and to make it clear that this is a test mount point
# We also use the presence of this mount point to determine if the test is running in docker
@pytest.fixture(autouse=True)
def cleanup_fs():
    """Make sure we are running in Docker and have write access to the mount point"""
    # Make sure we have write access to /mnt/docker-test-xfs
    assert os.access(
        MOUNT_POINT, os.W_OK
    ), f"This test must be run with write access to {MOUNT_POINT}"
    # Clean-up homes
    clear_home_directories(MOUNT_POINT)
    yield


def clear_home_directories(base_dir):
    """
    Clear the home directories from a given directory
    """
    for d in os.listdir(base_dir):
        # If the directory is not empty, remove the *.bin files
        # Not deleting everything in the directory to avoid accidental data loss
        for f in os.listdir(os.path.join(base_dir, d)):
            if f.endswith(".bin"):
                os.remove(os.path.join(base_dir, d, f))
        os.rmdir(os.path.join(base_dir, d))


@pytest.fixture
def quota_manager(tmp_path):
    """
    Fixture to create a pre-configured QuotaManager instance.

    This instance encodes the following assumptions:
    - The minimum project ID is 1000
    - There are no projects/profid entries
    """
    quota_manager = QuotaManager.instance(
        projid_file=os.fspath(tmp_path / "projid"),
        projects_file=os.fspath(tmp_path / "projects"),
        min_projid=1000,
        # Ensure the value of ~1000 in the quota output
        hard_quota=1000 / GIB_TO_KIB,
    )
    yield quota_manager


def create_home_directories(base_dir, homedirs):
    # create the homedirs
    for d in homedirs:
        os.mkdir(os.path.join(base_dir, d))


def test_reconcile_projids(quota_manager):
    # Loop over homedirs inside this test function, as we're testing statefulness
    for homedirs in [
        # base set of home directories
        {"a": 1001, "b": 1002, "c": 1003},
        # We remove 'c', but add 'd'. This should remove 'c' from projfiles, add 'd' with new id
        {"a": 1001, "b": 1002, "d": 1004},
        # We re-add 'c', which should give it a new id
        {"a": 1001, "b": 1002, "d": 1004, "c": 1005},
    ]:
        clear_home_directories(MOUNT_POINT)
        create_home_directories(MOUNT_POINT, homedirs)

        # Given this set of home directories, after the run, the projid file should have exactly these dirs with these ids
        quota_manager.paths = [MOUNT_POINT]
        quota_manager.reconcile_projfiles()

        with (
            open(quota_manager.projid_file, "rb") as projid_file,
            open(quota_manager.projects_file, "rb") as projects_file,
        ):
            projid_contents = projid_file.read().decode()
            projects_contents = projects_file.read().decode()

        homedir_paths = {os.path.join(MOUNT_POINT, k): v for k, v in homedirs.items()}

        expected_projid_contents = (
            OWNERSHIP_PREAMBLE
            + "\n".join([f"{k}:{v}" for k, v in homedir_paths.items()])
            + "\n"
        )
        expected_projects_contents = (
            OWNERSHIP_PREAMBLE
            + "\n".join([f"{v}:{k}" for k, v in homedir_paths.items()])
            + "\n"
        )

        assert projid_contents == expected_projid_contents
        assert projects_contents == expected_projects_contents


def test_missing_base_directory(quota_manager, tmp_path):
    """
    Test that reconcile_projfiles creates missing base directories
    """
    # Create a path that doesn't exist yet
    nonexistent_path = os.fspath(tmp_path / "nonexistent")
    quota_manager.paths = [nonexistent_path]

    # This should not raise FileNotFoundError
    quota_manager.reconcile_projfiles()

    # Verify the directory was created
    assert os.path.exists(nonexistent_path)
    assert os.path.isdir(nonexistent_path)

    # Verify the directory is owned by the desired user and group 1000:1000 by default
    state = os.stat(nonexistent_path)
    assert (state.st_uid, state.st_gid) == (1000, 1000)

    # Verify the files were created correctly (should be empty since no home dirs)
    with open(quota_manager.projid_file) as f:
        assert f.read() == OWNERSHIP_PREAMBLE
    with open(quota_manager.projects_file) as f:
        assert f.read() == OWNERSHIP_PREAMBLE


def test_exclude_dirs(quota_manager):
    """
    Test that we can exclude dirs from quota enforcement
    """
    quota_manager.paths = [MOUNT_POINT]

    # Reconcile with basic home directories
    create_home_directories(MOUNT_POINT, {"a": 1001, "b": 1002, "c": 1003})
    quota_manager.reconcile_step()

    applied_quotas = quota_manager.get_applied_quotas()
    assert applied_quotas[os.path.join(MOUNT_POINT, "a")] == {
        "blocks": {"soft": 0, "hard": 1000, "used": 0},
        "inodes": {"soft": 0, "hard": 0, "used": 1},
        "realtime": {"soft": 0, "hard": 0, "used": 0},
    }

    # Now reconcile with exclusions
    quota_manager.exclude = ["a"]
    quota_manager.reconcile_step()

    applied_quotas = quota_manager.get_applied_quotas()
    assert applied_quotas[os.path.join(MOUNT_POINT, "a")] == {
        "blocks": {"soft": 0, "hard": 0, "used": 0},
        "inodes": {"soft": 0, "hard": 0, "used": 1},
        "realtime": {"soft": 0, "hard": 0, "used": 0},
    }

    # Create a 2MB test file using a temporary file
    with tempfile.NamedTemporaryFile() as test_file:
        test_file.write(b"0" * 2 * 1024 * 1024)
        test_file.flush()

        # copy the file to /mnt/docker-test-xfs/b and ensure it fails
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_output(
                ["cp", test_file.name, os.path.join(MOUNT_POINT, "b", "2MB.bin")]
            )

        # copy the file to /mnt/docker-test-xfs/a that is excluded from quota and ensure it succeeds
        subprocess.check_output(
            ["cp", test_file.name, os.path.join(MOUNT_POINT, "a", "2MB.bin")]
        )


def test_config_file(tmp_path):
    """Test that the traitlets config file is loaded and used correctly"""
    config_file_path = tmp_path / "config.py"
    projects_path = os.fspath(tmp_path / "projects")
    projid_path = os.fspath(tmp_path / "projid")
    config_file_path.write_text(
        # Write test config
        textwrap.dedent(
            f"""
            c.QuotaManager.projects_file = {projects_path!r}
            c.QuotaManager.projid_file = {projid_path!r}
            c.QuotaManager.paths = [{MOUNT_POINT!r}]
            c.QuotaManager.hard_quota = 0.003 # 3MB
            c.QuotaManager.exclude = ["c", "d"]
            c.QuotaManager.quota_overrides = {{
                "override": 0.005,  # 5MB custom quota
                "both": 0.003,  # 3MB custom quota (should override exclude)
            }}
        """
        )
    )

    # Create QuotaManager instance with our config
    manager = QuotaManager()
    manager.initialize(["--config-file", os.fspath(config_file_path)])

    # Verify config values were loaded correctly
    assert manager.paths == [MOUNT_POINT]
    assert manager.hard_quota == 0.003
    assert manager.exclude == ["c", "d"]
    assert manager.projects_file == projects_path
    assert manager.projid_file == projid_path
    assert manager.quota_overrides == {
        "override": 0.005,  # 5MB custom quota
        "both": 0.003,  # 3MB custom quota (should override exclude)
    }


def test_config_file_override(tmp_path):
    """Test that the traitlets config file is loaded and used correctly"""
    config_file_path = tmp_path / "config.py"
    config_file_path.write_text(
        # Write test config
        textwrap.dedent(
            f"""
            c.QuotaManager.projects_file = {os.fspath(tmp_path / "projects")!r}
            c.QuotaManager.projid_file = {os.fspath(tmp_path / "projid")!r}
            c.QuotaManager.paths = [{MOUNT_POINT!r}]
            c.QuotaManager.hard_quota = 0.003 # 3MB
            c.QuotaManager.exclude = ["c", "d"]
        """
        )
    )
    # Test command line override
    manager = QuotaManager()
    manager.initialize(
        ["--config-file", os.fspath(config_file_path), "--hard-quota=0.001"]
    )

    assert manager.hard_quota == 0.001  # Should be overridden by CLI
    assert manager.paths == [MOUNT_POINT]  # Should still be from config file
    assert manager.exclude == ["c", "d"]  # Should still be from config file

    # Prepare environment
    homedirs = {"a": 1001, "b": 1002, "c": 1003, "d": 1004}
    create_home_directories(MOUNT_POINT, homedirs)

    manager.reconcile_step()

    # check that quota is enforced
    with tempfile.NamedTemporaryFile() as test_file:
        test_file.write(b"0" * 2 * 1024 * 1024)
        test_file.flush()

        # check that the file is too big to copy
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_output(
                [
                    "cp",
                    test_file.name,
                    os.path.join(MOUNT_POINT, "b", "2MB.bin"),
                ]
            )

        # check that directory a is excluded from quota
        subprocess.check_output(
            ["cp", test_file.name, os.path.join(MOUNT_POINT, "d", "2MB.bin")]
        )


def test_quota_overrides(quota_manager):
    """Test that quota overrides work correctly with different priority levels"""
    homedirs = {"regular": 1001, "excluded": 1002, "override": 1003, "both": 1004}
    create_home_directories(MOUNT_POINT, homedirs)

    quota_manager.paths = [MOUNT_POINT]
    quota_manager.hard_quota = 0.001  # 1MB default
    quota_manager.exclude = ["excluded", "both"]  # both is in exclude AND override
    quota_manager.quota_overrides = {
        "override": 0.005,  # 5MB custom quota
        "both": 0.003,  # 3MB custom quota (should override exclude)
    }

    # Apply the quotas
    quota_manager.reconcile_step()

    invariant_quota = {
        "inodes": {"soft": 0, "hard": 0, "used": 1},
        "realtime": {"soft": 0, "hard": 0, "used": 0},
    }

    applied_quotas = quota_manager.get_applied_quotas()

    # Test quota priorities:
    # Note that we are converting to GiB for comparison instead of KiB because
    # the exact KiB values in XFS quota output can vary slightly due to rounding
    # to nearest block size, so we use GiB for consistency.

    # 1. "regular": should get default hard_quota (0.001 GiB)
    assert applied_quotas[os.path.join(MOUNT_POINT, "regular")] == {
        "blocks": {
            "used": 0,
            "soft": 0,
            "hard":
            # Tolerance of 4k default block size
            pytest.approx(0.001 * GIB_TO_KIB, abs=DEFAULT_BLOCK_SIZE_KIB),
        },
        **invariant_quota,
    }
    # 2. "excluded": should get 0 quota (excluded)
    assert applied_quotas[os.path.join(MOUNT_POINT, "excluded")] == {
        "blocks": {"soft": 0, "hard": 0, "used": 0},
        **invariant_quota,
    }

    # 3. "override": should get custom quota (0.005 GiB)
    assert applied_quotas[os.path.join(MOUNT_POINT, "override")] == {
        "blocks": {
            "used": 0,
            "soft": 0,
            "hard":
            # Tolerance of 4k default block size
            pytest.approx(0.005 * GIB_TO_KIB, abs=DEFAULT_BLOCK_SIZE_KIB),
        },
        **invariant_quota,
    }

    # 4. "both": should get override quota, NOT excluded (0.003 GiB)
    # This tests that quota_overrides takes priority over exclude
    assert applied_quotas[os.path.join(MOUNT_POINT, "both")] == {
        "blocks": {
            "used": 0,
            "soft": 0,
            "hard":
            # Tolerance of 4k default block size
            pytest.approx(0.003 * GIB_TO_KIB, abs=DEFAULT_BLOCK_SIZE_KIB),
        },
        **invariant_quota,
    }

    # Test actual file operations to verify quotas work
    with (
        tempfile.NamedTemporaryFile() as small_file,
        tempfile.NamedTemporaryFile() as large_file,
    ):
        # Create a 2MB test file
        small_file.write(b"0" * 2 * 1024 * 1024)
        small_file.flush()

        # Create a 4MB test file
        large_file.write(b"0" * 4 * 1024 * 1024)
        large_file.flush()

        # Test "regular" directory (1MB quota) - should fail with 2MB file
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_output(
                [
                    "cp",
                    small_file.name,
                    os.path.join(MOUNT_POINT, "regular", "test.bin"),
                ]
            )

        # Test "excluded" directory (0 quota = unlimited) - should succeed with 2MB file
        subprocess.check_output(
            [
                "cp",
                small_file.name,
                os.path.join(MOUNT_POINT, "excluded", "test.bin"),
            ]
        )

        # Test "override" directory (5MB quota) - should succeed with 4MB file
        subprocess.check_output(
            [
                "cp",
                large_file.name,
                os.path.join(MOUNT_POINT, "override", "test.bin"),
            ]
        )

        # Test "both" directory (3MB quota due to override) - should succeed with 2MB but fail with 4MB
        subprocess.check_output(
            [
                "cp",
                small_file.name,
                os.path.join(MOUNT_POINT, "both", "test2mb.bin"),
            ]
        )

        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_output(
                [
                    "cp",
                    large_file.name,
                    os.path.join(MOUNT_POINT, "both", "test4mb.bin"),
                ]
            )


def test_metrics(quota_manager):
    homedirs = {"user": 1001}
    create_home_directories(MOUNT_POINT, homedirs)

    quota_manager.paths = [MOUNT_POINT]
    quota_manager.hard_quota = 0.004  # 4MB

    # Apply the quotas
    quota_manager.reconcile_step()

    target_file_path = os.path.join(MOUNT_POINT, "user", "test-file.bin")
    target_file_size_bytes = 2 * 1024 * 1024
    with open(target_file_path, "w") as f:
        # Create a 2MB test file
        f.write("0" * target_file_size_bytes)
        f.flush()

    quotas = quota_manager.get_applied_quotas()
    quota_manager.update_metrics(quotas)

    collected_dirsize_metric = list(metrics.TOTAL_SIZE.collect())[0]

    assert len(collected_dirsize_metric.samples) != 0
    assert (
        Sample(
            name="dirsize_total_size_bytes",
            labels={"directory": "user"},
            value=target_file_size_bytes,
        )
        in collected_dirsize_metric.samples
    )

    collected_hardlimit_metric = list(metrics.HARD_LIMIT.collect())[0]
    assert (
        Sample(
            name="dirsize_hard_limit_bytes",
            labels={"directory": "user"},
            # The value is in bytes, not gb (used by jupyterhub-home-nfs) or kb (used by xfs)
            value=pytest.approx(
                0.004 * 1024 * 1024 * 1024, abs=DEFAULT_BLOCK_SIZE_KIB * 1024
            ),
        )
        in collected_hardlimit_metric.samples
    )


def test_quota_overrides_cli(tmp_path):
    """Test that quota overrides can be set via CLI"""
    # Test CLI override (traitlets supports dict parsing from CLI)
    quota_manager = QuotaManager()
    quota_manager.initialize(
        [
            "--paths",
            MOUNT_POINT,
            "--projects-file",
            os.fspath(tmp_path / "projects"),
            "--projid-file",
            os.fspath(tmp_path / "projid"),
            "--hard-quota",
            "0.001",
            "--quota-overrides",
            "test=0.002",
        ]
    )

    # Verify config values
    assert quota_manager.hard_quota == 0.001
    assert quota_manager.quota_overrides == {"test": 0.002}  # GiB

    homedirs = {"test": 1001}
    create_home_directories(MOUNT_POINT, homedirs)

    # Apply the quotas
    quota_manager.reconcile_step()

    applied_quotas = quota_manager.get_applied_quotas()
    assert applied_quotas[os.path.join(MOUNT_POINT, "test")] == {
        "blocks": {
            "used": 0,
            "soft": 0,
            "hard":
            # Tolerance of 4k default block size
            pytest.approx(0.002 * GIB_TO_KIB, abs=DEFAULT_BLOCK_SIZE_KIB),
        },
        "inodes": {"soft": 0, "hard": 0, "used": 1},
        "realtime": {"soft": 0, "hard": 0, "used": 0},
    }, "Expected quota of 0.002 GiB for 'test'"


def test_quota_clear(quota_manager):
    """Test that quota clears between invocations"""
    homedirs = {"alpha": 1001, "beta": 1002, "gamma": 1003}
    create_home_directories(MOUNT_POINT, homedirs)

    quota_manager.paths = [MOUNT_POINT]
    quota_manager.hard_quota = 1  # 1GiB

    # Apply the quotas
    quota_manager.reconcile_step()

    # Determine the applied quotas for existing on-disk projects
    # (Requires up-to-date projfiles)
    applied_quotas = quota_manager.get_applied_quotas()

    for name in homedirs:
        path = os.path.join(MOUNT_POINT, name)
        assert applied_quotas[path] == {
            "blocks": {
                "used": 0,
                "soft": 0,
                "hard": 1048576,
            },
            "inodes": {"soft": 0, "hard": 0, "used": 1},
            "realtime": {"soft": 0, "hard": 0, "used": 0},
        }

    # Set ihard quota in an out-of-band way (this is not intended to be preserved by jupyterhub-home-nfs)
    subprocess.check_call(
        [
            "xfs_quota",
            "-x",
            "-c",
            f"limit -p ihard=10 {MOUNT_POINT}/beta",
            "-D",
            f"{quota_manager.projects_file}",
            "-P",
            f"{quota_manager.projid_file}",
        ]
    )

    # Ensure that beta is modified
    applied_quotas = quota_manager.get_applied_quotas()
    path = os.path.join(MOUNT_POINT, "beta")
    assert applied_quotas[path] == {
        "blocks": {
            "used": 0,
            "soft": 0,
            "hard": 1048576,
        },
        "inodes": {
            "used": 1,
            "soft": 0,
            "hard": 10,
        },
        "realtime": {
            "used": 0,
            "soft": 0,
            "hard": 0,
        },
    }
    # Ensure other directories are not
    for name in homedirs:
        if name == "beta":
            continue
        path = os.path.join(MOUNT_POINT, name)
        assert applied_quotas[path] == {
            "blocks": {
                "used": 0,
                "soft": 0,
                "hard": 1048576,
            },
            "inodes": {
                "used": 1,
                "soft": 0,
                "hard": 0,
            },
            "realtime": {
                "used": 0,
                "soft": 0,
                "hard": 0,
            },
        }

    # Now, reconciling will forcibly update the quota by unsetting ihard
    quota_manager.reconcile_step()

    # Let's confirm that
    applied_quotas = quota_manager.get_applied_quotas()
    for name in homedirs:
        path = os.path.join(MOUNT_POINT, name)
        assert applied_quotas[path] == {
            "blocks": {
                "used": 0,
                "soft": 0,
                "hard": 1048576,
            },
            "inodes": {
                "used": 1,
                "soft": 0,
                "hard": 0,
            },
            "realtime": {
                "used": 0,
                "soft": 0,
                "hard": 0,
            },
        }


def test_project_clear(quota_manager):
    """Test that project IDs clears between invocations"""
    homedirs = {"alpha": 1001, "beta": 1002, "gamma": 1003}
    create_home_directories(MOUNT_POINT, homedirs)

    quota_manager.paths = [MOUNT_POINT]
    quota_manager.hard_quota = 1  # 1GiB

    # Apply the quotas
    quota_manager.reconcile_step()

    # Check we first set proper project IDs
    applied_projects = quota_manager.get_applied_projects()
    for name, projid in homedirs.items():
        path = os.path.join(MOUNT_POINT, name)
        assert applied_projects[path] == projid

    # Update min proj ID
    quota_manager.min_projid = 2000

    # Apply changes to files (forcibly update projfiles)
    quota_manager.reconcile_step(projfiles_is_dirty=True)

    # Check we see proper project IDs
    applied_projects = quota_manager.get_applied_projects()
    for name, projid in homedirs.items():
        path = os.path.join(MOUNT_POINT, name)
        assert applied_projects[path] == projid + 1000
