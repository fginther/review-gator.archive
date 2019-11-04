#!/usr/bin/env python

import os
import shutil

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
    tox_return_code = lpmptox_runtox(source_repo, source_branch)
    if tox_return_code == 0:
        print("PASS")
        #if not os.path.isfile(tox_state):
        shutil.copy(success_svg, tox_state)
    else:
        print("FAIL")
        shutil.copy(error_svg, tox_state)
