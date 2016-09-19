#!/usr/bin/env python2

import os

files = [f for f in os.listdir(".") if f.endswith(".patch")]
files.sort()

for i in xrange(len(files)):
    newf = files[i]
    if files[i].endswith(".patch.patch"):
        newf = files[i][:-len(".patch")]
        pass

    newf = newf[5:]
    os.rename(files[i], newf)
    files[i] = newf

    print("Patch%d: %s" % (i + 1, newf))
    pass

print("")

for i in xrange(len(files)):
    print("%%patch%d -p1 -b .%s" % \
          (i + 1, files[i][:-len(".patch")].replace(" ", "-")))
    pass
