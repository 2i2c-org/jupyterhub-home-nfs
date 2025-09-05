import os
import subprocess
import tempfile
import textwrap
from pprint import pprint  # noqa: F401

import pytest

from jupyterhub_home_nfs.generate import OWNERSHIP_PREAMBLE, QuotaManager

MOUNT_POINT = "/mnt/docker-test-xfs"


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
    quota_manager = QuotaManager.instance(
        projid_file=os.fspath(tmp_path / "projid"),
        projects_file=os.fspath(tmp_path / "projects"),
        min_projid=1000,
        hard_quota=1000 / 1024**2,
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

    quota_output = subprocess.check_output(
        [
            "xfs_quota",
            "-x",
            "-c",
            "report -N -p",
            "-D",
            f"{quota_manager.projects_file}",
            "-P",
            f"{quota_manager.projid_file}",
        ]
    ).decode()
    # remove empty lines
    quota_output_lines = [line for line in quota_output.split("\n") if line.strip()]
    # We should see 4 lines in the output: 1 for the default project, and 3 for the homedirs a, b, c
    assert (
        len(quota_output_lines) == 4
    ), f"Expected 4 lines in quota output, got {len(quota_output_lines)} in {quota_output}"

    # Check that one line starts with "/mnt/docker-test-xfs/a"
    assert any(
        line.startswith(f"{MOUNT_POINT}/a") for line in quota_output_lines
    ), f"Expected one line to start with '{MOUNT_POINT}/a', got {quota_output_lines}"
    # Check that the line with "/mnt/docker-test-xfs/a" has a quota of 1000 since we haven't excluded it yet
    a_line = next(
        line for line in quota_output_lines if line.startswith(f"{MOUNT_POINT}/a")
    )
    assert (
        len(a_line.split()) == 6
    ), f"Expected 6 columns in line with '{MOUNT_POINT}/a', got {len(a_line.split())} in {a_line}"
    assert (
        a_line.split()[3] == "1000"
    ), f"Expected quota of 1000 for '{MOUNT_POINT}/a', got {a_line.split()[3]}"

    # Now reconcile with exclusions
    quota_manager.exclude = ["a"]
    quota_manager.reconcile_step()

    # Now test the output of "xfs_quota -x -c 'report -N -p'"
    # We should see the same number of projects as there are homedirs
    # and the quota should be set to the hard quota
    quota_output = subprocess.check_output(
        [
            "xfs_quota",
            "-x",
            "-c",
            "report -N -p",
            "-D",
            f"{quota_manager.projects_file}",
            "-P",
            f"{quota_manager.projid_file}",
        ]
    ).decode()
    quota_output_lines = [line for line in quota_output.split("\n") if line.strip()]
    # We should see 4 lines in the output: 1 for the default project, and 3 for the homedirs a, b, c
    assert (
        len(quota_output_lines) == 4
    ), f"Expected 4 lines in quota output, got {len(quota_output_lines)} in {quota_output}"

    # Check that one line starts with "/mnt/docker-test-xfs/a"
    assert any(
        line.startswith(f"{MOUNT_POINT}/a") for line in quota_output_lines
    ), f"Expected one line to start with '{MOUNT_POINT}/a', got {quota_output_lines}"
    # Check that the line with "/mnt/docker-test-xfs/a" has a quota of 0 (a quota of 0 means no quota is enforced)
    a_line = next(
        line for line in quota_output_lines if line.startswith(f"{MOUNT_POINT}/a")
    )
    assert (
        len(a_line.split()) == 6
    ), f"Expected 6 columns in line with '{MOUNT_POINT}/a', got {len(a_line.split())} in {a_line}"
    assert (
        a_line.split()[3] == "0"
    ), f"Expected quota of 0 for '{MOUNT_POINT}/a', got {a_line.split()[3]}"

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

    # Check quota output to verify settings
    quota_output = subprocess.check_output(
        [
            "xfs_quota",
            "-x",
            "-c",
            "report -N -p",
            "-D",
            f"{quota_manager.projects_file}",
            "-P",
            f"{quota_manager.projid_file}",
        ]
    ).decode()
    quota_output_lines = [line for line in quota_output.split("\n") if line.strip()]

    # Helper function to get quota for a directory
    def get_quota_for_dir(dirname):
        line = next(
            line
            for line in quota_output_lines
            if line.startswith(f"{MOUNT_POINT}/{dirname}")
        )
        return int(line.split()[3])  # hard quota is 4th column

    # Test quota priorities:
    # Note that we are converting to GiB for comparison instead of KiB because
    # the exact KiB values in XFS quota output can vary slightly due to rounding
    # to nearest block size, so we use GiB for consistency.

    # 1. "regular": should get default hard_quota (0.001 GiB)
    assert get_quota_for_dir("regular") / (1024 * 1024) == pytest.approx(
        0.001, abs=0.0001
    )

    # 2. "excluded": should get 0 quota (excluded)
    assert get_quota_for_dir("excluded") == 0

    # 3. "override": should get custom quota (0.005 GiB)
    assert get_quota_for_dir("override") / (1024 * 1024) == pytest.approx(
        0.005, abs=0.0001
    )

    # 4. "both": should get override quota, NOT excluded (0.003 GiB)
    # This tests that quota_overrides takes priority over exclude
    assert get_quota_for_dir("both") / (1024 * 1024) == pytest.approx(0.003, abs=0.0001)

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
    assert quota_manager.quota_overrides == {"test": 0.002}

    homedirs = {"test": 1001}
    create_home_directories(MOUNT_POINT, homedirs)

    # Apply the quotas
    quota_manager.reconcile_step()

    # Check that the override was applied (2MB = 2048KB)
    quota_output = subprocess.check_output(
        [
            "xfs_quota",
            "-x",
            "-c",
            "report -N -p",
            "-D",
            f"{quota_manager.projects_file}",
            "-P",
            f"{quota_manager.projid_file}",
        ]
    ).decode()
    quota_output_lines = [line for line in quota_output.split("\n") if line.strip()]

    test_line = next(
        line for line in quota_output_lines if line.startswith(f"{MOUNT_POINT}/test")
    )
    assert int(test_line.split()[3]) / (1024 * 1024) == pytest.approx(
        0.002, abs=0.0001
    ), f"Expected quota of 0.002 GiB for 'test', got {int(test_line.split()[3]) / (1024 * 1024)} GiB"
