#!/usr/bin/env python2

from __future__ import print_function

import argparse
import glob
import os
import re
import shutil
import subprocess
import tempfile
import time

import git
from git import Repo

from spec_parse import Spec

def verify(args):
    if args.updateonly and args.newversion:
        print("Error: can't specify both new version and updateonly!")
        exit(1)

    r = Repo(".")
    args.srcrepo = r

    if args.branch:
        r.heads[args.branch].checkout()
        pass
    else:
        args.branch = str(r.active_branch)
        pass
    if args.branch == "rawhide":
        args.branch = "master"
        pass

    if not args.tag:
        args.tag = r.git.describe("--abbrev=0", "--tags")
        pass
    r.tags[args.tag] # check it exists

    if not args.packagedir:
        cwd = r.working_dir.split(os.sep)
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

        args.packagedir = os.sep.join([os.getenv("HOME"), cwd, args.branch])
        pass
    args.packagerepo = Repo(args.packagedir)

    assert(len(glob.glob(os.path.join(args.packagedir, "*.spec"))) == 1)

    global log
    if args.verbose:
        log = lambda s: print(s)
        pass
    else:
        log = lambda s: None
        pass

    return args

def produce_patches(args):
    os.chdir(args.srcrepo.working_dir)
    for p in glob.glob("*.patch"):
        os.remove(p)
        pass
    args.srcrepo.git.format_patch("-N", args.tag + "..")

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

def get_msg(args):
    # this needs GitPython >= 1.7 in order to be nice
    msg = "- " + str(args.srcrepo.git.log("HEAD~1..").split("\n")[4].strip())

    # vi is absolutely not a reasonable default.  Keep this simple.
    editor = os.getenv("EDITOR", "nano")

    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(msg)
    fname = f.name
    f.close()

    subprocess.check_call(["%s %s" % (editor, fname)], shell=True)

    msg = open(fname, "r").read()
    os.unlink(fname)

    if msg[-1] != '\n':
        msg += "\n"
        pass
    return msg

def bookkeep(s, args):
    release = re.match("Release:\s+(\d+)", s.release).group(1)
    relnum = int(release) + 1

    if args.newversion:
        version = re.match("Version:\s+(.*)", s.version).group(1)
        s.version = s.version.replace(version, args.newversion, 1)
        relnum = 1
        pass

    s.release = s.release.replace(release, str(relnum), 1)

    msg = get_msg(args)

    version = re.match("Version:\s+(.*)", s.version).group(1)
    use_sep = "> - " in s.changelog[:80] # check first line
    sep = "- " if use_sep else ""
    d = time.strftime("%a %b %d %Y")
    new_log = "* %s %s %s%s-%s\n%s\n" % \
              (d, "Robbie Harwood <rharwood@redhat.com>",
               sep, version, relnum, msg)
    s.changelog = new_log + s.changelog

    return msg

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

    pr = args.packagerepo
    pr.heads[args.branch].checkout()

    try:
        pr.index.remove(["*.patch"], working_tree=True)
        pass
    except git.exc.GitCommandError:
        pass

    for p in glob.glob(os.path.join(repodir, "*.patch")):
        shutil.move(p, '.')
        pass
    pr.index.add(["*.patch"])
    return

def commit(args, cl_entry):
    cl_entry = cl_entry[2:] # remove "- " from first line
    cl_entry = cl_entry.replace("\n", "\n\n", 1) # space out the body
    cl_entry = cl_entry.replace("\n- ", "\n")
    while cl_entry[-1] == '\n':
        cl_entry = cl_entry[:-1]
        pass

    args.packagerepo.index.commit(cl_entry)
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Munge a patched git tree into an existing spec file.")
    parser.add_argument("-b", dest="branch", default=None,
                        help="branch to work from (default: current)")
    parser.add_argument("-d", dest="packagedir", default=None,
                        help="package repository dir (default: from branch)")
    parser.add_argument("-n", dest="newversion", default=None,
                        help="bump version specified (default: don't)")
    parser.add_argument("-N", dest="nocommit", action="store_true",
                        help="leave changes uncommitted (default: commit)")
    parser.add_argument("-p", dest="prefix", default=1, type=int,
                        help="prefix level to use with patch(1) (default: 1)")
    parser.add_argument("-t", dest="tag", default=None,
                        help="git tag to base patches on (default: ask git)")
    parser.add_argument("-u", dest="updateonly", action="store_true",
                        help="no new version in spec file (default: false)")
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
        cl_entry = bookkeep(s, args)
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
    args.packagerepo.index.add(["*.spec"])

    log("Moving patches...")
    move_patches(args)

    if not args.nocommit and not args.updateonly:
        log("Committing changes...")
        commit(args, cl_entry)
        pass

    log("Done!")
    exit(0)
