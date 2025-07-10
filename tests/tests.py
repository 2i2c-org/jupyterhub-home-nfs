import os
import subprocess
import tempfile
import textwrap
from pprint import pprint  # noqa: F401

import pytest

from jupyterhub_home_nfs.generate import (
    OWNERSHIP_PREAMBLE,
    QuotaManager,
    reconcile_projfiles,
    reconcile_quotas,
)

# This is the mount point defined in mount-xfs.sh
# It is named docker-test-xfs to avoid conflicts with the host's mount point
# and to make it clear that this is a test mount point
# We also use the presence of this mount point to determine if the test is running in docker
MOUNT_POINT = "/mnt/docker-test-xfs"


@pytest.fixture(autouse=True)
def check_mount_point():
    """Make sure we are ruuning in docker and have write access to the mount point"""
    # Make sure we have write access to /mnt/docker-test-xfs
    assert os.access(
        MOUNT_POINT, os.W_OK
    ), f"This test must be run with write access to {MOUNT_POINT}"


def _reset_quotas(base_dir, projects_file, projid_file, homedirs):
    """
    Given a list of homedirs, reset the quotas by excluding them from the quota enforcement
    """
    # clear out the existing homedirs
    for d in os.listdir(base_dir):
        # If the directory is not empty, remove the *.bin files
        # Not deleting everything in the directory to avoid accidental data loss
        for f in os.listdir(os.path.join(base_dir, d)):
            if f.endswith(".bin"):
                os.remove(os.path.join(base_dir, d, f))
        os.rmdir(os.path.join(base_dir, d))

    # create the homedirs
    for d in homedirs:
        os.mkdir(os.path.join(base_dir, d))

    # Empty the projects and projid files
    projects_file.truncate(0)
    projid_file.truncate(0)

    # reconcile the projects and projid files
    reconcile_projfiles([MOUNT_POINT], projects_file.name, projid_file.name, 1000)
    reconcile_quotas(projid_file.name, 1000, [], {})


def test_reconcile_projids():
    # Given this set of home directories, after each run, the projid file should have exactly these dirs with these ids
    homedirs_sequence = [
        # base set of home directories
        {"a": 1001, "b": 1002, "c": 1003},
        # We remove 'c', but add 'd'. This should remove 'c' from projfiles, add 'd' with new id
        {"a": 1001, "b": 1002, "d": 1004},
        # We re-add 'c', which should give it a new id
        {"a": 1001, "b": 1002, "d": 1004, "c": 1005},
    ]

    with (
        tempfile.NamedTemporaryFile() as projects_file,
        tempfile.NamedTemporaryFile() as projid_file,
        tempfile.TemporaryDirectory() as base_dir,
    ):
        for homedirs in homedirs_sequence:

            for d in os.listdir(base_dir):
                # using rmdir so we don't accidentally rm -rf things
                os.rmdir(os.path.join(base_dir, d))

            for s in homedirs:
                os.mkdir(os.path.join(base_dir, s))

            reconcile_projfiles([base_dir], projects_file.name, projid_file.name, 1000)

            projects_file.flush()
            projid_file.flush()
            projid_file.seek(0)
            projects_file.seek(0)

            projid_contents = projid_file.read().decode()
            projects_contents = projects_file.read().decode()

            expected_projid_contents = (
                OWNERSHIP_PREAMBLE
                + "\n".join(
                    [f"{os.path.join(base_dir, k)}:{v}" for k, v in homedirs.items()]
                )
                + "\n"
            )
            expected_projects_contents = (
                OWNERSHIP_PREAMBLE
                + "\n".join(
                    [f"{v}:{os.path.join(base_dir, k)}" for k, v in homedirs.items()]
                )
                + "\n"
            )

            assert projid_contents == expected_projid_contents
            assert projects_contents == expected_projects_contents


def test_exclude_dirs():
    """
    Test that we can exclude dirs from quota enforcement
    """
    homedirs = {"a": 1001, "b": 1002, "c": 1003}
    exclude_dirs = ["a"]

    projects_file_path = "/etc/projects"
    projid_file_path = "/etc/projid"
    base_dir = MOUNT_POINT

    with (
        open(projects_file_path, "w+b") as projects_file,
        open(projid_file_path, "w+b") as projid_file,
    ):
        _reset_quotas(base_dir, projects_file, projid_file, list(homedirs.keys()))

        quota_output = subprocess.check_output(
            ["xfs_quota", "-x", "-c", "report -N -p"]
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
        reconcile_projfiles([base_dir], projects_file.name, projid_file.name, 1000)
        reconcile_quotas(projid_file.name, 1000, exclude_dirs, {})

        # Now test the output of "xfs_quota -x -c 'report -N -p'"
        # We should see the same number of projects as there are homedirs
        # and the quota should be set to the hard quota
        quota_output = subprocess.check_output(
            ["xfs_quota", "-x", "-c", "report -N -p"]
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


def test_config_file():
    """Test that the traitlets config file is loaded and used correctly"""
    homedirs = {"a": 1001, "b": 1002, "c": 1003, "d": 1004}

    projects_file_path = "/etc/projects"
    projid_file_path = "/etc/projid"
    base_dir = MOUNT_POINT

    with (
        open(projects_file_path, "w+b") as projects_file,
        open(projid_file_path, "w+b") as projid_file,
    ):
        _reset_quotas(base_dir, projects_file, projid_file, list(homedirs.keys()))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as config_file:

            # Write test config
            config_content = textwrap.dedent(
                f"""
                c.QuotaManager.projects_file = "{projects_file.name}"
                c.QuotaManager.projid_file = "{projid_file.name}"
                c.QuotaManager.paths = ["{base_dir}"]
                c.QuotaManager.hard_quota = 0.003 # 3MB
                c.QuotaManager.exclude = ["c", "d"]
            """
            )

            config_file.write(config_content)
            config_file.flush()

            # Create QuotaManager instance with our config
            manager = QuotaManager()
            manager.initialize(["--config-file", config_file.name])

            # Verify config values were loaded correctly
            assert manager.paths == [base_dir]
            assert manager.hard_quota == 0.003
            assert manager.exclude == ["c", "d"]
            assert manager.projects_file == projects_file.name
            assert manager.projid_file == projid_file.name

            # Test command line override
            manager = QuotaManager()
            manager.initialize(
                ["--config-file", config_file.name, "--hard-quota=0.001"]
            )
            assert manager.hard_quota == 0.001  # Should be overridden by CLI
            assert manager.paths == [base_dir]  # Should still be from config file
            assert manager.exclude == ["c", "d"]  # Should still be from config file

            manager._reconcile_projfiles()
            manager._reconcile_quotas()

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


def test_quota_overrides():
    """Test that quota overrides work correctly with different priority levels"""
    homedirs = {"regular": 1001, "excluded": 1002, "override": 1003, "both": 1004}

    projects_file_path = "/etc/projects"
    projid_file_path = "/etc/projid"
    base_dir = MOUNT_POINT

    with (
        open(projects_file_path, "w+b") as projects_file,
        open(projid_file_path, "w+b") as projid_file,
    ):
        _reset_quotas(base_dir, projects_file, projid_file, list(homedirs.keys()))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as config_file:
            # Write test config with quota overrides
            config_content = textwrap.dedent(
                f"""
                c.QuotaManager.projects_file = "{projects_file.name}"
                c.QuotaManager.projid_file = "{projid_file.name}"
                c.QuotaManager.paths = ["{base_dir}"]
                c.QuotaManager.hard_quota = 0.001  # 1MB default
                c.QuotaManager.exclude = ["excluded", "both"]  # both is in exclude AND override
                c.QuotaManager.quota_overrides = {{
                    "override": 0.005,  # 5MB custom quota
                    "both": 0.003       # 3MB custom quota (should override exclude)
                }}
                """
            )

            config_file.write(config_content)
            config_file.flush()

            # Create QuotaManager instance with our config
            manager = QuotaManager()
            manager.initialize(["--config-file", config_file.name])

            # Verify config values were loaded correctly
            assert manager.hard_quota == 0.001
            assert manager.exclude == ["excluded", "both"]
            assert manager.quota_overrides == {"override": 0.005, "both": 0.003}

            # Apply the quotas
            manager._reconcile_projfiles()
            manager._reconcile_quotas()

            # Check quota output to verify settings
            quota_output = subprocess.check_output(
                ["xfs_quota", "-x", "-c", "report -N -p"]
            ).decode()
            quota_output_lines = [
                line for line in quota_output.split("\n") if line.strip()
            ]

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
            assert get_quota_for_dir("both") / (1024 * 1024) == pytest.approx(
                0.003, abs=0.0001
            )

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


def test_quota_overrides_cli():
    """Test that quota overrides can be set via CLI"""
    homedirs = {"test": 1001}

    projects_file_path = "/etc/projects"
    projid_file_path = "/etc/projid"
    base_dir = MOUNT_POINT

    with (
        open(projects_file_path, "w+b") as projects_file,
        open(projid_file_path, "w+b") as projid_file,
    ):
        _reset_quotas(base_dir, projects_file, projid_file, list(homedirs.keys()))

        # Test CLI override (traitlets supports dict parsing from CLI)
        manager = QuotaManager()
        manager.initialize(
            [
                "--paths",
                base_dir,
                "--projects-file",
                projects_file.name,
                "--projid-file",
                projid_file.name,
                "--hard-quota",
                "0.001",
                "--quota-overrides",
                "test=0.002",
            ]
        )

        # Verify config values
        assert manager.hard_quota == 0.001
        assert manager.quota_overrides == {"test": 0.002}

        # Apply the quotas
        manager._reconcile_projfiles()
        manager._reconcile_quotas()

        # Check that the override was applied (2MB = 2048KB)
        quota_output = subprocess.check_output(
            ["xfs_quota", "-x", "-c", "report -N -p"]
        ).decode()
        quota_output_lines = [line for line in quota_output.split("\n") if line.strip()]

        test_line = next(
            line
            for line in quota_output_lines
            if line.startswith(f"{MOUNT_POINT}/test")
        )
        assert int(test_line.split()[3]) / (1024 * 1024) == pytest.approx(
            0.002, abs=0.0001
        ), f"Expected quota of 0.002 GiB for 'test', got {int(test_line.split()[3]) / (1024 * 1024)} GiB"
