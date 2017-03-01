#!/usr/bin/python2

import glob
import os
import re
import subprocess
import sys
import time

from spec_parse import Spec

argv = sys.argv

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
        print(s)
        exit(1)
    return

def usage():
    print("Usage: %s [-p#] packagedir basetag" % argv[0])
    exit(1)

prefix = 1
while len(argv) > 3 and argv[1].startswith("-"):
    if argv[1].startswith("-p"):
        prefix = int(argv[1][2:])
        pass
    else:
        usage()
        pass

    del(argv[1])
    pass

if len(argv) < 3:
    usage()
    pass

packagedir = argv[1]
test("ls " + packagedir + "/.git", "package repo does not exist!")
test("ls " + packagedir + "/*.spec", "spec file not found!")

basetag = argv[2]
test("git log " + basetag + ".." + basetag, "problem with upstream repo!")

print("Everything looks okay; let's go...")

run("rm -f *.patch", fail=True)
run("git format-patch -N %s.." % basetag)

print("Patches produced correctly...")

files = [f for f in os.listdir(".") if f.endswith(".patch")]
files.sort() # because git auto-numbers them for us

for (i, newf) in enumerate(files):
    newf = files[i]
    if newf.endswith(".patch.patch"):
        newf = newf[:-len(".patch")]
        pass

    # remove git's initial numbering now that order is set
    newf = newf[5:]
    os.rename(files[i], newf)
    files[i] = newf

    # strip out git's version at the bottom
    with open(newf, "r") as f:
        d = f.read()
        pass
    d = d.replace(d[d.index("\n-- \n"):], "\n")
    with open(newf, "w") as f:
        f.write(d)
        pass
    pass

# heavy machinery
s = Spec(glob.glob(packagedir + "/*.spec")[0])
new_patches = []
for (k, v) in s.patches:
    if v in files:
        new_patches.append((k, v))
        pass
    pass

nextind = 0
for f in files:
    e = [k for (k, v) in new_patches if v == f]
    if len(e) > 0:
        if e[0] < nextind:
            nextind = -1
            break

        nextind = e[0] + 1
        continue

    new_patches.append((nextind, f))
    nextind += 1
    pass

if nextind == -1:
    print("Warning: Failed to preserve existing numbering!")

    # Keep backporting clearly easy
    nextind = max([i for (i, _) in s.patches])
    new_patches = list(enumerate(files, nextind))
    pass

s.patches = new_patches

relnum = int(re.match("Release:\s+(\d+)", s.release).group(1))
s.release = s.release.replace(str(relnum), str(relnum + 1), 1)

version = re.match("Version:\s+(.*)", s.version).group(1)
use_sep = "> - " in s.changelog[:80] # check first line
sep = "- " if use_sep else ""
d = time.strftime("%a %b %d %Y")
new_log = "* %s %s %s%s-%s\n- TODO edit me\n\n" % \
          (d, "Robbie Harwood <rharwood@redhat.com>",
           sep, version, relnum+1)
s.changelog = new_log + s.changelog

s.sync_to_file()

print("")

print("In case you don't have %autosetup:")
for (i, newf) in new_patches:
    print("%%patch%d -p%d -b .%s" % \
          (i, prefix, newf[:-len(".patch")].replace(" ", "-")))
    pass

print("Moving patches...")

repodir = run("pwd")[:-1] # newlines

os.chdir(packagedir)
run("git rm -f *.patch", fail=True)
run("mv " + repodir + "/*.patch .")
run("git add *.patch")
