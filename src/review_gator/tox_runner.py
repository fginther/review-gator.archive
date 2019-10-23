#!/usr/bin/env python

import os
import shutil

import git
from lpmptox import runtox as lpmptox_runtox


def prep_tox_state(output_directory=None, mp_id=None):
    os.makedirs(output_directory, exist_ok=True)
    abs_vendor_path = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), "vendor")
    tox_state = os.path.join(output_directory, "{}.svg".format(mp_id))
    clock_svg = os.path.join(abs_vendor_path, "clock.svg")
    shutil.copy(clock_svg, tox_state)


def run_tox(source_repo, source_branch, output_directory=None, mp_id=None):
    abs_vendor_path = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), "vendor")
    tox_state = os.path.join(output_directory, "{}.svg".format(mp_id))
    clock_svg = os.path.join(abs_vendor_path, "clock.svg")
    error_svg = os.path.join(abs_vendor_path, "error.svg")
    success_svg = os.path.join(abs_vendor_path, "success.svg")
    shutil.copy(clock_svg, tox_state)
    try:
        tox_return_code = lpmptox_runtox(source_repo, source_branch)
    except git.exc.GitCommandError as git_exc:
        # If there was a git exception it should not exit as run_tox is
        # called as a parallel set of jobs and one job failing should not
        # cause the whole process to exit. Instead print the exception
        print("** There was an exception running git commands for repo "
              "{} branch {} **".format(source_repo, source_branch))
        print(git_exc)
        tox_return_code = 1
    if tox_return_code == 0:
        print("PASS for repo {} branch {}".format(source_repo, source_branch))
        shutil.copy(success_svg, tox_state)
    else:
        print("FAIL for repo {} branch {}".format(source_repo, source_branch))
        shutil.copy(error_svg, tox_state)
