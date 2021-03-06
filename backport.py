#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

from distutils.version import LooseVersion

from fedora import chroot

def run_hard(s: str) -> None:
    try:
        subprocess.check_output(s.split(" "))
    except subprocess.CalledProcessError:
        print(f"While running $({s}) in {os.getcwd()}",
              file=sys.stderr)
        exit(-1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backport manager.")
    # parser.add_argument("-n", dest="numcommits", default=0, type=int,
    #                     help="commits on top to pull back (default: all)")
    # parser.add_argument("-c", dest="commitid", default=None,
    #                     help="a single commit to pull back (default: don't)")
    parser.add_argument("-t", dest="to", default=None, required=True,
                        help="dist version to stop at")

    args = parser.parse_args()

    srcrepo_path = os.getcwd().split('/')
    branch = srcrepo_path.pop()
    reponame = srcrepo_path.pop()
    package = reponame.split(".git")[0]

    if branch.startswith("rhel-"):
        dist = "rhel"
    elif branch.startswith("f"):
        dist = "fedora"
    elif branch == "rawhide":
        dist = "fedora"
        branch = "master"
    else:
        print("Bad repo layout!", file=sys.stderr)
        exit(-1)

    pkg_repo_base = "%s/%s.%s" % (os.getenv("HOME"), package, dist)
    os.chdir(pkg_repo_base)

    branches = os.listdir()
    branches.sort(key=LooseVersion)
    branches.reverse()
    if branch != "master":
        branches.remove("master")
    if args.to not in branches:
        print("Yo, fix your branches", file=sys.stderr)
        exit(-1)

    for b in branches:
        if b >= branch:
            continue
        elif b < args.to:
            break

        os.chdir(b)
        run_hard("git merge --ff-only %s" % branch)
        os.chdir("..")

    for b in branches:
        if b >= branch:
            continue
        elif b < args.to:
            break

        p = "rhpkg" if dist == "rhel" else "fedpkg"
        cmd = f"cd {pkg_repo_base}/{b} && {p} push && {p} build --nowait"
        chroot(cmd, os.getuid())
