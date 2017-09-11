#!/usr/bin/python2

from __future__ import print_function

import argparse
import glob
import os
import re
import subprocess
import sys
import time

from spec_parse import Spec

def run(cmd, stderr=None, fail=False):
    # I don't want to think about globbing
    res = ""
    try:
        res = subprocess.check_output(cmd, shell=True, stderr=stderr)
        pass
    except subprocess.CalledProcessError as e:
        if not fail:
            raise e
        res = e.output
        pass
    return res

def test(cmd, s):
    try:
        run(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        log(s)
        exit(1)
    return

def verify(args):
    if args.updateonly and args.newversion:
        print("Error: can't specify both new version and updateonly!")
        exit(1)

    if args.branch:
        run("git checkout " + args.branch, stderr=subprocess.STDOUT)
        pass
    else:
        args.branch = run("git branch | grep '^\* '")[2:-1]
        pass
    if args.branch == "rawhide":
        args.branch = "master"
        pass

    if not args.tag:
        args.tag = run("git describe --abbrev=0 --tags")[:-1]
        pass

    if not args.packagedir:
        top = run("git rev-parse --show-toplevel")[:-1]
        cwd = os.getcwd().split(os.sep)
        while cwd[-1] in ["rawhide", args.branch]:
            del(cwd[-1])
            pass
        cwd = cwd[-1].split(".")[0]

        if "rhel" in args.branch:
            cwd += ".rhel"
            pass
        else:
            cwd += ".fedora"
            pass

        args.packagedir = os.sep.join([os.getenv("HOME"), cwd])
        pass

    global log
    if args.verbose:
        log = lambda s: print(s)
        pass
    else:
        log = lambda s: None
        pass

    try:
        run("ls " + args.packagedir + "/.git", stderr=subprocess.STDOUT)
        pass
    except subprocess.CalledProcessError:
        args.packagedir += "/" + args.branch
        test("ls " + args.packagedir + "/.git",
             "package repo %s does not exist!" % args.packagedir)
        pass

    test("ls " + args.packagedir + "/*.spec", "spec file not found!")

    test("git log " + args.tag + ".." + args.tag,
         "problem with upstream repo (tag: %s)!" % args.tag)

    return args

def produce_patches(args):
    run("rm -f *.patch", fail=True, stderr=subprocess.STDOUT)
    run("git format-patch -N %s.." % args.tag)

    incoming_patches = [f for f in os.listdir(".") if f.endswith(".patch")]
    incoming_patches.sort() # because git auto-numbers them for us

    for (i, newp) in enumerate(incoming_patches):
        newp = incoming_patches[i]

        # legacy, pre-me patches
        if newp.endswith(".patch.patch"):
            newp = newp[:-len(".patch")]
            pass

        # remove git's initial numbering now that order is set
        newp = newp[5:]
        os.rename(incoming_patches[i], newp)
        incoming_patches[i] = newp

        # strip out git's version at the bottom
        with open(newp, "r") as f:
            d = f.read()
            pass
        d = d.replace(d[d.index("\n-- \n"):], "\n")
        with open(newp, "w") as f:
            f.write(d)
            pass
        pass
    return incoming_patches

def apply_patches(s, incoming_patches):
    patches_old = []
    for (k, v) in s.patches:
        if v in incoming_patches:
            patches_old.append((k, v))
            pass
        pass

    nextind = 0
    patches_res = []
    while len(incoming_patches) > 0:
        p = incoming_patches[0]
        del(incoming_patches[0]) # I'm the best at what I doooooooo

        e = [(k, v) for (k, v) in patches_old if v == p]
        if len(e) > 0: # patch carried over from old set
            if e[0][0] < nextind: # indexing constraint violated
                incoming_patches.insert(0, p)
                break

            patches_res.append(e[0])
            nextind = e[0][0] + 1
            continue

        # patch is new - set nextind to next smallest unused
        if len(patches_old) != 0:
            nextind = 1 + max([k for (k, _) in patches_res])
            pass
        patches_res.append((nextind, p))
        nextind += 1
        pass

    if len(incoming_patches) > 0:
        log("Warning: Failed to preserve existing numbering!")

        # Keep backporting clearly easy, but keep the common prefix
        nextind = 1 + max([k for (k, _) in patches_res])
        patches_res += list(enumerate(incoming_patches, nextind))
        pass

    s.patches = patches_res
    return patches_res

def bookkeep(s, args):
    release = re.match("Release:\s+(\d+)", s.release).group(1)
    relnum = int(release) + 1

    if args.newversion:
        version = re.match("Version:\s+(.*)", s.version).group(1)
        s.version = s.version.replace(version, args.newversion, 1)
        relnum = 1
        pass

    s.release = s.release.replace(release, str(relnum), 1)

    log("Enter changelog (C-d when done):")
    msg = sys.stdin.read()

    version = re.match("Version:\s+(.*)", s.version).group(1)
    use_sep = "> - " in s.changelog[:80] # check first line
    sep = "- " if use_sep else ""
    d = time.strftime("%a %b %d %Y")
    new_log = "* %s %s %s%s-%s\n%s\n" % \
              (d, "Robbie Harwood <rharwood@redhat.com>",
               sep, version, relnum, msg)
    s.changelog = new_log + s.changelog
    return

def handle_autosetup(s, patches):
    # TODO(rharwood) patches are assumed to occupy only a single block here
    # I may never care enough to fix this assumption
    nopatches = [l for l in s.prep.split("\n") if not l.startswith("%patch")]
    insind = 0
    while not nopatches[insind].startswith("%setup"):
        insind += 1
        pass
    nopatches.insert(insind + 1, patches)
    s.prep = "\n".join(nopatches)
    return

def generate_patch_section(patches_res):
    patches = ""
    for (i, newf) in patches_res:
        patches += "%%patch%d -p%d -b .%s\n" % \
                   (i, args.prefix, newf[:-len(".patch")].replace(" ", "-"))
        pass
    patches = patches[:-1]
    return patches

def move_patches(args):
    repodir = os.getcwd()

    os.chdir(args.packagedir)

    bchange = run("git checkout " + args.branch, stderr=subprocess.STDOUT)
    if not bchange.startswith("Already on '"):
        sys.stderr.write(bchange)
        pass

    run("git rm -f *.patch", fail=True)
    run("mv " + repodir + "/*.patch .")
    run("git add *.patch")
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Munge a patched git tree into an existing spec file.")
    parser.add_argument("-p", dest="prefix", default=1, type=int,
                        help="prefix level to use with patch(1) (default: 1)")
    parser.add_argument("-b", dest="branch", default=None,
                        help="branch to work from (default: current)")
    parser.add_argument("-t", dest="tag", default=None,
                        help="git tag to base patches on (default: ask git)")
    parser.add_argument("-u", dest="updateonly", action="store_true",
                        help="no new version in spec file (default: false)")
    parser.add_argument("-n", dest="newversion", default=None,
                        help="bump version specified (default: don't)")
    parser.add_argument("-d", dest="packagedir", default=None,
                        help="package repository dir (default: from branch)")
    parser.add_argument("-v", dest="verbose", action="store_true",
                        help="increase verbosity (default: be quiet)")
    args = parser.parse_args()
    args = verify(args)
    log("Everything looks okay; let's go...")

    incoming_patches = produce_patches(args)
    log("Patches produced correctly...")

    s = Spec(glob.glob(args.packagedir + "/*.spec")[0])
    log("Spec file parsed...")

    patches_res = apply_patches(s, incoming_patches)
    log("New patches applied...")

    if not args.updateonly:
        bookkeep(s, args)
        log("Kept books...")
        pass

    patches = generate_patch_section(patches_res)
    if "%autosetup" not in s.prep:
        handle_autosetup(s, patches)
        log("Synced autosetup data...")
        pass
    log("In case %autosetup detection fails:")
    log("")
    log(patches)
    log("")

    s.sync_to_file()
    log("Wrote out spec file!")

    log("Moving patches...")
    move_patches(args)

    log("Done!")
    exit(0)
