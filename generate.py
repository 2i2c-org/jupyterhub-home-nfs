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

Your home directories must already be on an XFS file system, with prjquota
mount option enabled.

The script runs two reconciliation loops:

1. Entries in /etc/projects & /etc/projid for all home directories in the
   given paths
2. Correct xfs_quota project & limit setup for each entry in /etc/projid

This is run in a loop, and should provide fairly robust quotaing setup.

This script *owns* /etc/projects and /etc/projid. If there are entries
there that aren't put in there by this script, they will be removed!
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


def reconcile_projfiles(paths, projects_file_path, projid_file_path, min_projid):
    """
    Make sure each homedir in paths has an appropriate projid entry.

    This 'owns' /etc/projets & /etc/projid as well. If there are extra entries there,
    they will be removed!
    """
    # Fetch existing home directories
    # Sort to provide consistent ordering across runs
    homedirs = sorted([ent.path for path in paths for ent in os.scandir(path) if ent.is_dir()])
    print(homedirs)

    # Fetch list of projects in /etc/projid file, assumed to sync'd to /etc/projects file
    projects = parse_projids(projid_file_path)
    print(projects)

    # We have to write /etc/projid & /etc/projects if they aren't completely in sync
    projid_file_dirty = sorted(list(projects.keys())) != sorted(homedirs)

    if projid_file_dirty:
        # Check if there are any homedirs that aren't in projects
        new_homes = [h for h in homedirs if h not in projects]

        # Make sure /etc/projid & /etc/projects are in sync with home dirs
        if new_homes:
            for home in new_homes:
                # Ensure an entry exists in projects
                if home not in projects:
                    projects[home] = max(projects.values() or [min_projid]) + 1
                    projid_file_dirty = True
                    print(f'Found new project {home}')

        # Remove projects that don't have corresponding homedirs
        projects = {k: v for k, v in projects.items() if k in homedirs}


        # FIXME: make this an atomic write
        with open(projects_file_path, 'w') as projects_file, open(projid_file_path, 'w') as projid_file:
            for path, id in projects.items():
                projid_file.write(f'{path}:{id}\n')
                projects_file.write(f'{id}:{path}\n')

        print(f'Writing /etc/projid and /etc/projects')

def reconcile_quotas(projid_file_path, hard_quota_kb):
    """
    Make sure each project in /etc/projid has correct hard quota set
    """

    # Get current set of projects on disk
    projects = parse_projids(projid_file_path)
    # Fetch quota information from xfs_quota
    quotas = get_quotas()

    # Check for projects that don't have any nor correct quota
    changed_projects = [p for p in projects if quotas.get(p, {}) .get('hard') != hard_quota_kb]

    # Make sure xfs_quotas is in sync
    if changed_projects:
        for project in changed_projects:
            mountpoint = mountpoint_for(project)
            if project not in quotas:
                subprocess.check_call([
                    'xfs_quota', '-x', '-c',
                    f'project -s {project}',
                    mountpoint
                ])
                print(f'Setting up xfs_quota project for {project}')
            if project not in quotas or quotas[project]['hard'] != hard_quota_kb:
                subprocess.check_call([
                    'xfs_quota', '-x', '-c',
                    f'limit -p bhard={hard_quota_kb}k {project}',
                    mountpoint
                ])
                print(f'Setting limit for project {project} to {hard_quota_kb}k')



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
        reconcile_projfiles(args.paths, args.projects_file, args.projid_file, args.min_projid)
        reconcile_quotas(args.projid_file, hard_quota_kb)
        time.sleep(args.wait_time)

if __name__ == '__main__':
    main()
