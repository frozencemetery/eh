#!/usr/bin/env python3

import argparse
import glob
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import time

import git # type: ignore
from git import Repo

from delay import wait_gate, wait_rpmdiff, wait_covscan
#from errata import Erratum
from fedora import chroot
from spec_parse import Spec

from typing import Callable, List, Tuple

Patchset = List[Tuple[int, str]]

log: Callable[[str], None]

def verify(args: argparse.Namespace) -> argparse.Namespace:
    r = Repo(".")
    args.srcrepo = r

    if args.branch:
        r.heads[args.branch].checkout()
    else:
        args.branch = str(r.active_branch)
    if args.branch == "rawhide":
        args.branch = "master"

    if not args.tag:
        args.tag = r.git.describe("--abbrev=0", "--tags")
    r.tags[args.tag] # check it exists

    cwd = r.working_dir.split(os.sep)
    while cwd[-1] in ["rawhide", args.branch]:
        del(cwd[-1])
    cwd = cwd[-1].split(".")[0]

    if "rhel" in args.branch:
        cwd += ".rhel"
    else:
        cwd += ".fedora"
    args.packagedir = os.sep.join([str(os.getenv("HOME")), cwd, args.branch])
    args.packagerepo = Repo(args.packagedir)
    args.package = args.packagedir.split("/")[-2].split(".")[0]

    assert(len(glob.glob(os.path.join(args.packagedir, "*.spec"))) == 1)

    global log
    if args.verbose:
        log = lambda s: print(s)
    else:
        log = lambda s: None

    if args.bz:
        m = re.search("[0-9]+", args.bz)
        assert(m)
        args.bz = m.group(0)
        if "rhel" not in args.branch:
            print("WARN: Fedora doesn't support bugzilla manipulation",
                  file=sys.stderr)

    if not args.skip:
        # brew doesn't properly handle ccache collections, and we need to
        # check that we have a TGT for the right realm anyway else it'll bomb
        # out later
        user = pwd.getpwuid(os.getuid()).pw_name
        realm = "REDHAT.COM" if cwd.endswith(".rhel") else "FEDORAPROJECT.ORG"
        try:
            subprocess.check_call(f"kswitch -p {user}@{realm}", shell=True)
        except subprocess.CalledProcessError:
            try:
                subprocess.check_call(f"kinit {user}@{realm}", shell=True)
            except subprocess.CalledProcessError as e:
                print(f"Creds not found! ({e})", file=sys.stderr)
                exit(1)

    return args

def produce_patches(args: argparse.Namespace) -> List[str]:
    os.chdir(args.srcrepo.working_dir)
    for p in glob.glob("*.patch"):
        os.remove(p)
    args.srcrepo.git.format_patch("-N", args.tag + "..")

    incoming_patches = [f for f in os.listdir(".") if f.endswith(".patch")]
    incoming_patches.sort() # because git auto-numbers them for us

    for (i, newp) in enumerate(incoming_patches):
        newp = incoming_patches[i]

        # legacy, pre-me patches
        if newp.endswith(".patch.patch"):
            newp = newp[:-len(".patch")]

        # remove git's initial numbering now that order is set
        newp = newp[5:]
        os.rename(incoming_patches[i], newp)
        incoming_patches[i] = newp

        # strip out git's version at the bottom
        with open(newp, "r") as f:
            d = f.read()
        d = d.replace(d[d.index("\n-- \n"):], "\n")
        with open(newp, "w") as f:
            f.write(d)
    return incoming_patches

def apply_patches(s: Spec, incoming_patches: List[str]) -> Patchset:
    patches_old = []
    for (k, v) in s.patches:
        if v in incoming_patches:
            patches_old.append((k, v))

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
            nextind = 1 + max([k for (k, _) in patches_res] + [0])
            pass
        patches_res.append((nextind, p))
        nextind += 1

    if len(incoming_patches) > 0:
        log("Warning: Failed to preserve existing numbering!")

        # Keep backporting clearly easy, but keep the common prefix
        nextind = 1 + max([k for (k, _) in patches_res])
        patches_res += list(enumerate(incoming_patches, nextind))

    s.patches = patches_res
    return patches_res

def get_msg(args: argparse.Namespace) -> str:
    # this needs GitPython >= 1.7 in order to be nice
    msg = "- " + str(args.srcrepo.git.log("HEAD~1..").split("\n")[4].strip())
    if args.bz:
        msg += "\n- Resolves: #%s" % args.bz

    # vi is absolutely not a reasonable default.  Keep this simple.
    editor = os.getenv("EDITOR", "nano")

    f = tempfile.NamedTemporaryFile(delete=False)
    f.write((msg + "\n").encode('utf-8'))
    fname = f.name
    f.close()

    subprocess.check_call(["%s %s" % (editor, fname)], shell=True)

    msg = open(fname, "r").read()
    os.unlink(fname)

    if msg[-1] != '\n':
        msg += "\n"
    return msg

def bookkeep(s: Spec, args: argparse.Namespace) -> str:
    m = re.match(r"Release:[^\d]*(\d+)%\{\?dist\}", s.release)
    assert(m)
    release = m.group(1)
    releases = release.split(".")
    relnum = int(releases[-1]) + 1
    releases[-1] = str(relnum)
    curr = ".".join(releases)

    # We want to strip out anything after dist here
    s.release = s.release.replace(release, curr, 1)
    s.release = s.release[:s.release.index("%{?dist}") + len("%{?dist}")]

    msg = get_msg(args)

    m = re.match(r"Version:\s+(.*)", s.version)
    assert(m)
    version = m.group(1)
    use_sep = "> - " in s.changelog[:80] # check first line
    sep = "- " if use_sep else ""
    d = time.strftime("%a %b %d %Y")
    l = f"* {d} Robbie Harwood <rharwood@redhat.com> {sep}{version}-{curr}"
    s.changelog = f"{l}\n{msg}\n{s.changelog}"

    return msg

def handle_autosetup(s: Spec, patches: str) -> None:
    # TODO(rharwood) patches are assumed to occupy only a single block here
    # I may never care enough to fix this assumption
    nopatches = [l for l in s.prep.split("\n") if not l.startswith("%patch")]
    insind = 0
    while not nopatches[insind].startswith("%setup"):
        insind += 1
    nopatches.insert(insind + 1, patches)
    s.prep = "\n".join(nopatches)
    return

def generate_patch_section(patches_res: Patchset) -> str:
    patches = ""
    for (i, newf) in patches_res:
        patches += "%%patch%d -p%d -b .%s\n" % \
                   (i, args.prefix, newf[:-len(".patch")].replace(" ", "-"))
    patches = patches[:-1]
    return patches

def move_patches(args: argparse.Namespace) -> None:
    repodir = os.getcwd()
    os.chdir(args.packagedir)

    pr = args.packagerepo
    pr.heads[args.branch].checkout()

    try:
        pr.index.remove(["*.patch"], working_tree=True)
    except git.exc.GitCommandError:
        pass

    for p in glob.glob(os.path.join(repodir, "*.patch")):
        shutil.move(p, '.')
    pr.index.add(["*.patch"])
    return

def commit(args: argparse.Namespace, cl_entry: str) -> None:
    cl_entry = cl_entry[2:] # remove "- " from first line
    cl_entry = cl_entry.replace("\n", "\n\n", 1) # space out the body
    cl_entry = cl_entry.replace("\n- ", "\n")
    while cl_entry[-1] == '\n':
        cl_entry = cl_entry[:-1]

    args.packagerepo.index.commit(cl_entry)
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Munge a patched git tree into an existing spec file.")
    parser.add_argument("-b", dest="branch", default=None,
                        help="branch to work from (default: current)")
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
    parser.add_argument("-s", dest="skip", action="store_true",
                        help="skip doing builds (default: do it)")
    parser.add_argument("-d", dest="dontpatch", action="store_true",
                        help="start at build step (default: also do patches)")
    parser.add_argument("bz", default=None, nargs='?',
                        help="bugzilla to reference (default: bad person)")
    parser.add_argument("errata", default=None, nargs='?',
                        help="errata to update (default: by hand, later)")
    args = parser.parse_args()
    args = verify(args)
    log("Everything looks okay; let's go...")

    if not args.dontpatch:
        incoming_patches = produce_patches(args)
        log("Patches produced correctly...")

    # Some people think it's a great idea to abuse their ProvenPackager status
    # to touch things that are better left alone.  They could not be more
    # wrong.  I hate this.
    args.packagerepo.git.pull("--autostash")

    s = Spec(glob.glob(args.packagedir + "/*.spec")[0])
    log("Spec file parsed...")

    if not args.dontpatch:
        patches_res = apply_patches(s, incoming_patches)
        log("New patches applied...")

    if not args.updateonly and not args.dontpatch:
        cl_entry = bookkeep(s, args)
        log("Kept books...")

    if not args.dontpatch:
        patches = generate_patch_section(patches_res)
        if "%autosetup" not in s.prep:
            handle_autosetup(s, patches)
            log("Synced autosetup data...")
        log("In case %autosetup detection fails:")
        log("")
        log(patches)
        log("")

        log("Moving patches...")
        move_patches(args)

        if s.sync_to_file():
            print("Can't continue; problem syncing spec file!")
            exit(-1)

        log("Wrote out spec file!")
        args.packagerepo.index.add(["*.spec"])

        if not args.nocommit and not args.updateonly:
            log("Committing changes...")
            commit(args, cl_entry)

    log("Checking SRPM generation...")
    pkg = "rhpkg" if "rhel" in args.branch else "fedpkg"
    cmd = f"cd {args.packagedir} && {pkg} prep"
    r = chroot(cmd)
    if r:
        print("SRPM generation failed!")
        exit(-1)

    if not args.skip:
        log("Doing build gunk...")
        pkg = "rhpkg" if "rhel" in args.branch else "fedpkg"
        cmd = f"cd {args.packagedir} && {pkg} push && {pkg} build"
        if args.bz and "rhel" in args.branch:
            cmd = "bugzilla login &&" + cmd
            cmd += " && rhpkg bugzilla --modified --fixed-in"
        r = chroot(cmd)
        if r:
            print("Build failed!")
            exit(-1)

        if args.bz and "rhel" in args.branch:
            # check for gating
            d = args.branch[5:6]
            if int(d) >= 8:
                wait_gate(args.package)

            # pv = args.branch.upper() + ".GA"
            # vr = cl_entry.split(' ')[-1]
            # nvr = f"{args.package}-{vr}.el{d}"

            # e = Erratum(args.package, pv, args.bz)
            # assert(not e.add_build(pv, nvr))

            # wait_rpmdiff(args.package)
            # wait_covscan(args.package)

            # assert(not e.set_state("QE"))

    log("Done!")
