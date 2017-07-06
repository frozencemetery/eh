#!/usr/bin/python2

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
        print(s)
        exit(1)
    return

parser = argparse.ArgumentParser(
    description="Munge a patched git tree into an existing spec file.")
parser.add_argument("-p", "--prefix", default=1, type=int,
                    help="prefix level to use with patch(1) (default: 1)")
parser.add_argument("packagedir", help="location of package git repository")
parser.add_argument("basetag", help="git tag patches are based on")
args = parser.parse_args()

test("ls " + args.packagedir + "/.git", "package repo does not exist!")
test("ls " + args.packagedir + "/*.spec", "spec file not found!")

test("git log " + args.basetag + ".." + args.basetag,
     "problem with upstream repo!")

print("Everything looks okay; let's go...")

run("rm -f *.patch", fail=True)
run("git format-patch -N %s.." % args.basetag)

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
s = Spec(glob.glob(args.packagedir + "/*.spec")[0])
new_patches = []
for (k, v) in s.patches:
    if v in files:
        new_patches.append((k, v))
        pass
    pass

nextind = 0
while len(files) > 0:
    f = files[0]
    del(files[0]) # I'm the best at what I doooooooo
    e = [k for (k, v) in new_patches if v == f]
    if len(e) > 0:
        if e[0] < nextind:
            break
        nextind = e[0] + 1
        continue

    # are we done adding existing files?
    # set difference - find any in s.patches that are still in files
    break_again = False
    for (_, v) in s.patches:
        if v in files:
            # existing numbering is toast
            nextind = max([k for (k, _) in new_patches + s.patches]) + 1
            # break twice
            break_again = True
            break
        pass
    if break_again:
        files.insert(0, f)
        break
    pass

if len(files) > 0:
    print("Warning: Failed to preserve existing numbering!")

    # Keep backporting clearly easy
    new_patches += list(enumerate(files, nextind))
    pass

s.patches = new_patches

relnum = int(re.match("Release:\s+(\d+)", s.release).group(1))
s.release = s.release.replace(str(relnum), str(relnum + 1), 1)

print("Enter changelog (C-d when done):")
msg = sys.stdin.read()

version = re.match("Version:\s+(.*)", s.version).group(1)
use_sep = "> - " in s.changelog[:80] # check first line
sep = "- " if use_sep else ""
d = time.strftime("%a %b %d %Y")
new_log = "* %s %s %s%s-%s\n%s\n" % \
          (d, "Robbie Harwood <rharwood@redhat.com>",
           sep, version, relnum+1, msg)
s.changelog = new_log + s.changelog

patches = ""
for (i, newf) in new_patches:
    patches += "%%patch%d -p%d -b .%s\n" % \
               (i, args.prefix, newf[:-len(".patch")].replace(" ", "-"))
    pass
patches = patches[:-1]

if "%autosetup" not in s.prep:
    # TODO(rharwood) patches are assumed to occupy only a single block here
    # I may never care enough to fix this assumption
    nopatches = [l for l in s.prep.split("\n") if not l.startswith("%patch")]
    insind = 0
    while not nopatches[insind].startswith("%setup"):
        insind += 1
        pass
    nopatches.insert(insind + 1, patches)
    s.prep = "\n".join(nopatches)
    pass

s.sync_to_file()

print("")

print("In case %autosetup detection fails:")
print(patches)

print("Moving patches...")

repodir = run("pwd")[:-1] # newlines

os.chdir(args.packagedir)
run("git rm -f *.patch", fail=True)
run("mv " + repodir + "/*.patch .")
run("git add *.patch")
