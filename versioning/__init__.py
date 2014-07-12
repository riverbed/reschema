# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

"""
This module contains code for interacting with git repositories. It is
used to determine an appropriate version number from either the local
git repository tags or from a version file.
"""

from __future__ import unicode_literals, print_function, division
import os
import inspect
from subprocess import Popen, PIPE


def verify_repository(pkg_file):
    """Raise an error if this source file is not in tracked by git."""
    dirname = os.path.dirname(pkg_file)
    basename = os.path.basename(pkg_file)

    cwd = os.getcwd()
    try:
        os.chdir(dirname)
        process = Popen(['git', 'ls-files', basename, '--error-unmatch'],
                        stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
    finally:
        os.chdir(cwd)

    if stderr:
        # Not a git repo
        raise EnvironmentError(stderr)


def call_git_branch():
    """Return 'git branch' output."""
    process = Popen(['git', 'branch'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()

    if stderr:
        # Not a git repo
        raise EnvironmentError(stderr)
    else:
        return stdout.strip()


def get_branch(input=None):
    """Parse branch from 'git branch' output.

    :param input: Return string from 'git branch' command
    """
    if input is None:
        input = call_git_branch()

    line = [ln for ln in input.split('\n') if ln.startswith('*')][0]
    return line.split()[-1]


def call_git_describe(abbrev=None):
    """Return 'git describe' output.

    :param abbrev: Integer to use as the --abbrev value for git describe
    """
    cmd = ['git', 'describe']

    # --abbrev and --long are mutually exclusive 'git describe' options
    if abbrev is not None:
        cmd.append('--abbrev={0}'.format(abbrev))
    else:
        cmd.append('--long')

    process = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()

    if stderr:
        # Not a git repo
        raise EnvironmentError(stderr)
    else:
        return stdout.strip()


def parse_tag():
    """Parse version info from 'git describe' and return as dict.

    A typical full git tag contains four pieces of information: the repo name,
    the version, the number of commits since the last tag, and the SHA-1 hash
    that identifies the commit.

    :return: A dict with items 'version', 'commits', and 'sha'

    """
    long_tag = call_git_describe()
    base_tag = call_git_describe(abbrev=0)

    # Parse number of commits and sha
    try:
        raw_version_str = long_tag.replace(base_tag, '')
        commits, sha = [part for part in raw_version_str.split('-') if part]
    except ValueError:
        # Tuple unpacking failed, so probably an incorrect tag format was used.
        print('Parsing error: The git tag seems to be malformed.\n---')
        raise

    return {'version': base_tag,
            'commits': commits,
            'sha': sha.strip(), }


def get_version(pkg_file=None, v_file='RELEASE-VERSION'):
    """Return <tag>.post<commits> style version string.

    :param pkg_file: Some filename in the package, used to test if this
       is a live git repostitory (defaults to caller's file)

    :param v_file: Fallback path name to a file where release_version is saved
    """

    if pkg_file is None:
        parent_frame = inspect.stack()[1]
        pkg_file = inspect.getabsfile(parent_frame[0])

    try:
        verify_repository(pkg_file)
        git_info = parse_tag()
        branch = get_branch()
        if branch == 'master':
            if git_info['commits'] == '0':
                version = git_info['version']
            else:
                version = '%s.post%s' % (git_info['version'], git_info['commits'])
        else:
            # Still allow building of the package, but give it
            # a different version.  The use of g_ ensures that
            # python will give it the proper ordering after final
            # but before post:
            #   6.0.0                   -> 6, 0, 0, *final
            #   6.0.0-g_branch-34-hash  -> 6, 0, 0, *g_branch, 34 hash
            #   6.0.0-post34            -> 6, 0, 0, *post, 34
            version = '%s-g_%s-%s-%s' % (
                git_info['version'], branch, git_info['commits'], git_info['sha'])

        with open(v_file, 'w') as f:
            f.write(version)

    except EnvironmentError:
        # Not a git repository, so fall back to reading RELEASE-VERSION
        if (os.path.exists(v_file)):
            with open(v_file, 'r') as f:
                version = f.read().strip()
        else:
            version = 'unknown'

    except AssertionError:
        print('Release version string can only be derived from master branch.'
              '\n---')
        raise EnvironmentError('Current branch not master: %s' % branch)

    return version
