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
"""
import os
import time
import subprocess
import argparse


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


def populate_projects(path, projects, min_projid):
    changed = []
    for ent in os.scandir(path):
        if ent.path not in projects:
            if projects:
                new_id = max(projects.values()) + 1
            else:
                new_id = min_projid
            projects[ent.path] = new_id
            print(f"Wrote new project {ent.path} with id {new_id}")
            changed.append(ent.path)
    return changed

def xfs_quota_admin(command, mountpoint):
    """
    Run arbitrary xfs_quota command on a given mountpoint
    """
    subprocess.check_call(['xfs_quota', '-x', '-c', command, mountpoint])

def mountpoint_for(path):
    """
    Return mount point containing file / directory in path

    xfs_quota wants to know which fs to operate on
    """
    return subprocess.check_output(['df', '--output=target', path]).decode().strip().split('\n')[-1].strip()

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
    args = argparser.parse_args()

    while True:
        projects = parse_projids(args.projid_file)
        changed = []
        for path in args.paths:
            changed += populate_projects(path, projects, args.min_projid)

        if changed:
            print(f"New projects, setting up quotas")
            with open(args.projects_file, 'w') as projects_file, open(args.projid_file, 'w') as projid_file:
                for path, id in projects.items():
                    projid_file.write(f'{path}:{id}\n')
                    projects_file.write(f'{id}:{path}\n')
            for changed_project in changed:
                mountpoint = mountpoint_for(changed_project)
                xfs_quota_admin(f'project -s {changed_project}', mountpoint)
                xfs_quota_admin(f'limit -p bhard=20g {changed_project}', mountpoint)

        time.sleep(args.wait_time)

if __name__ == '__main__':
    main()
