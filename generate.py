#!/usr/bin/env python3
"""
Maintain user home directory quotas on XFS.

Many JupyterHubs use NFS for home directories. While kubernetes
offers memory & CPU isolation, disk quotas for NFS is hard to come
by. No hosted NFS service (EFS, Filestore, etc) offer quotas, and
most common file systems only offer per-userid quotas. XFS offers
'project' quotas, which are checked against any given directory. That
is what we want for our hubs!

This script can be run as a daemon in a machine acting as an
NFS server, setting up quotas with XFS as each home directory appears.
There can be a few seconds lag between the time the home directory appears
and the quota is set, but that should be ok for now (we can fix that with
inotify if we need to).

This script will:

1. Discover home directories inside a given set of paths
2. Ensure they have a deterministic entry in /etc/projects & /etc/prjoid
3. Run appropriate xfs_quota commands to set quotas for those directories
4. Watch for new home directories and repeat the process.

Your home directories must already be on an XFS file system, with prjquota
mount option enabled.

Runs as a reconciliation loop. It tries to keep the following pieces in
sync:

1. List of home directories (from paths given)
2. Project ID files `/etc/project` and `/etc/projids`
3. XFS quota project setup presence (via `xfs_quota`)
4. XFS quota limits given.
"""
import sys
import os
import time
import subprocess
import argparse
import itertools


def parse_projids(path):
    """
    Parse a projids file, returning mapping of paths to project IDs
    """
    projects = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                splits = line.split(':', 2)
                projects[splits[0]] = int(splits[1])
    return projects

def mountpoint_for(path):
    """
    Return mount point containing file / directory in path

    xfs_quota wants to know which fs to operate on
    """
    return subprocess.check_output(['df', '--output=target', path]).decode().strip().split('\n')[-1].strip()


def get_quotas():
    output = subprocess.check_output([
        'xfs_quota', '-x', '-c',
        'report -N -p'
    ]).decode().strip()
    quotas = {}
    for line in output.split('\n'):
        path, used, soft, hard, warn, grace = line.split()
        # Everything here is in kb, since that's what xfs_quota reports things in
        quotas[path] = {
            'used': int(used),
            'soft': int(soft),
            'hard': int(hard),
            'warn': int(warn),
            'grace': grace
        }
    return quotas


def write_projfiles(projects, projects_file_path, projid_file_path):
    with open(projects_file_path, 'w') as projects_file, open(projid_file_path, 'w') as projid_file:
        for path, id in projects.items():
            projid_file.write(f'{path}:{id}\n')
            projects_file.write(f'{id}:{path}\n')

def main():

    argparser = argparse.ArgumentParser()
    argparser.add_argument('paths', nargs='+',
        help='Paths to scan for home directories'
    )
    argparser.add_argument('--projects-file', default='/etc/projects')
    argparser.add_argument('--projid-file', default='/etc/projid')
    argparser.add_argument('--min-projid', default=1000, type=int,
        help="Project IDs will be generated starting from this number"
    )
    argparser.add_argument('--wait-time', default=30, type=int,
        help='Number of seconds to wait between runs'
    )
    argparser.add_argument('--hard-quota', default=10, type=float,
        help='Hard quota limit (in GB) to set for all home directories'
    )
    args = argparser.parse_args()

    # xfs_quota reports in kb
    hard_quota_kb = int(args.hard_quota * 1024 * 1024)

    while True:
        # Fetch existing home directories
        homedirs = [ent.path for path in args.paths for ent in os.scandir(path) if ent.is_dir()]
        # Fetch list of projects in /etc/projid file, assumed to sync'd to /etc/projects file
        projects = parse_projids(args.projid_file)
        # Fetch quota information from xfs_quota
        quotas = get_quotas()

        # Check if there are any homedirs that aren't in projects
        changed_entries = [h for h in homedirs if h not in projects]
        # Check for home directories that don't have correct quota
        changed_entries += [h for h in homedirs if h in quotas and quotas[h]['hard'] != hard_quota_kb]

        # Make sure /etc/projid & /etc/projects are in sync with home dirs
        if changed_entries:
            projid_file_dirty = False
            for entry in changed_entries:
                # Ensure an entry exists in projects
                if entry not in projects:
                    projects[entry] = max(projects.values() or [args.min_projid]) + 1
                    projid_file_dirty = True
                    print(f'Found new project {entry}')

            if projid_file_dirty:
                write_projfiles(projects, args.projects_file, args.projid_file)
                print(f'Writing /etc/projid and /etc/projects')

        # Make sure xfs_quotas is in sync
        # /etc/projid & /etc/projects need to be already in sync before this can work
        if changed_entries:
            for entry in changed_entries:
                mountpoint = mountpoint_for(entry)
                if entry not in quotas:
                    subprocess.check_call([
                        'xfs_quota', '-x', '-c',
                        f'project -s {entry}',
                        mountpoint
                    ])
                    print(f'Setting up xfs_quota project for {entry}')
                if entry not in quotas or quotas[entry]['hard'] != hard_quota_kb:
                    print(quotas[entry])
                    subprocess.check_call([
                        'xfs_quota', '-x', '-c',
                        f'limit -p bhard={hard_quota_kb}k {entry}',
                        mountpoint
                    ])
                    print(f'Setting limit for project {entry} to {hard_quota_kb}k')

        time.sleep(args.wait_time)

if __name__ == '__main__':
    main()
