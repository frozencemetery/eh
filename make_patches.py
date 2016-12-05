#!/usr/bin/env python2

import os
import subprocess
import sys

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

argv = sys.argv
argc = len(sys.argv)

if argc < 3:
    print("Usage: %s packagedir basetag")
    exit(1)

packagedir = argv[1]
test("ls " + packagedir + "/.git", "package repo does not exist!")

basetag = argv[2]
test("git log " + basetag + ".." + basetag, "problem with upstream repo!")

print("Everything looks okay; let's go...")

run("git format-patch -N %s.." % basetag)

print("Patches produced correctly...")

files = [f for f in os.listdir(".") if f.endswith(".patch")]
files.sort() # because git auto-numbers them for us

for (i, newf) in enumerate(files):
    if files[i].endswith(".patch.patch"):
        newf = files[i][:-len(".patch")]
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

for (i, newf) in enumerate(files):
    print("Patch%d: %s" % (i + 1, newf))
    pass

print("")

# not necessary in all configurations, but leaving it in anyway
for (i, newf) in enumerate(files):
    print("%%patch%d -p1 -b .%s" % \
          (i + 1, files[i][:-len(".patch")].replace(" ", "-")))
    pass

print("Moving patches...")

repodir = run("pwd")[:-1] # newlines

os.chdir(packagedir)
run("git rm -f *.patch", fail=True)
run("mv " + repodir + "/*.patch .")
run("git add *.patch")
