#!/usr/bin/env python2

import os

files = [f for f in os.listdir(".") if f.endswith(".patch")]
files.sort() # because git auto-numbers them for us

for i in xrange(len(files)):
    newf = files[i]
    if files[i].endswith(".patch.patch"):
        newf = files[i][:-len(".patch")]
        pass

    # remove git's initial numbering now that order is set
    newf = newf[5:]
    os.rename(files[i], newf)
    files[i] = newf

    print("Patch%d: %s" % (i + 1, newf))
    pass

print("")

# not necessary in all configurations, but leaving it in anyway
for i in xrange(len(files)):
    print("%%patch%d -p1 -b .%s" % \
          (i + 1, files[i][:-len(".patch")].replace(" ", "-")))
    pass
