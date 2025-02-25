import os
import tempfile
from generate import reconcile_projfiles, OWNERSHIP_PREAMBLE
import subprocess


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

    with tempfile.NamedTemporaryFile() as projects_file, tempfile.NamedTemporaryFile() as projid_file, tempfile.TemporaryDirectory() as base_dir:

        for homedirs in homedirs_sequence:

            for d in os.listdir(base_dir):
                # using rmdir so we don't accidentally rm -rf things
                os.rmdir(os.path.join(base_dir, d))

            for s in homedirs:
                os.mkdir(os.path.join(base_dir, s))

            reconcile_projfiles(
                [base_dir], projects_file.name, projid_file.name, 1000, []
            )

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
    Test that we can exclude dirs from quota reconciliation
    """
    homedirs = {"a": 1001, "b": 1002, "c": 1003}
    exclude_dirs = ["a"]
    with tempfile.NamedTemporaryFile() as projects_file, tempfile.NamedTemporaryFile() as projid_file, tempfile.TemporaryDirectory() as base_dir:
        for d in os.listdir(base_dir):
            # using rmdir so we don't accidentally rm -rf things
            os.rmdir(os.path.join(base_dir, d))

        for s in homedirs:
            os.mkdir(os.path.join(base_dir, s))

        # First reconcile without any exclusions
        reconcile_projfiles([base_dir], projects_file.name, projid_file.name, 1000, [])
        # make sure we have all the homedirs
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

        # Now reconcile with exclusions
        reconcile_projfiles(
            [base_dir], projects_file.name, projid_file.name, 1000, exclude_dirs
        )

        projects_file.flush()
        projid_file.flush()
        projid_file.seek(0)
        projects_file.seek(0)

        projid_contents = projid_file.read().decode()
        projects_contents = projects_file.read().decode()

        expected_homedirs = {k: v for k, v in homedirs.items() if k not in exclude_dirs}

        expected_projid_contents = (
            OWNERSHIP_PREAMBLE
            + "\n".join(
                [
                    f"{os.path.join(base_dir, k)}:{v}"
                    for k, v in expected_homedirs.items()
                ]
            )
            + "\n"
        )
        expected_projects_contents = (
            OWNERSHIP_PREAMBLE
            + "\n".join(
                [
                    f"{v}:{os.path.join(base_dir, k)}"
                    for k, v in expected_homedirs.items()
                ]
            )
            + "\n"
        )

        assert projid_contents == expected_projid_contents
        assert projects_contents == expected_projects_contents
