#!/usr/bin/python2

# sections:
# (start of file)
# %description
# any number of %package - %description pairs
# %prep
# %build
# %check
# %install
# %clean
# any amount of %post-related stuff
# any number of %files sections
# %changelog

import re

# Do not assume a field not being present here means it is not in the spec
# file.  We do not parse out everything.
class Spec:
    def __init__(self, path):
        self.path = path
        with open(path, "r") as f:
            self.data = f.read()
            pass

        # changelog macros don't matter, so pull it out first
        rest, _, self.changelog = self.data.partition("%changelog\n")
        # now it is safe to go through the file in either order, so I do it
        # backward because it makes most sense to me

        # tosses out everything after %install / %check
        rest, _, _ = rest.rpartition("%install\n")
        rest, _, _ = rest.rpartition("%check\n")
        rest, _, self.build = rest.rpartition("%build\n")
        rest, _, self.prep = rest.rpartition("%prep\n")

        # tosses out all descriptions and stuff
        rest, _, _ = rest.rpartition("%description")
        self.release = re.search("\nRelease: (.*)\n", rest).group(1)

        # probably keep track of numbering here
        self.sources = [s.group(1) for s in
                        re.finditer("^Source\d+: (.*)$", rest, re.MULTILINE)]
        self.patches = [p.group(1) for p in
                        re.finditer("^Patch\d+: (.*)$", rest, re.MULTILINE)]

        self.preamble, _, rest = self.data.partition("%description\n")
        self.pkgdata, _, rest = rest.partition("%prep\n")
        self.prep, _, rest = rest.partition("%build\n")
        self.build, _, rest = rest.partition("\n")
        
        return

    # Will not delete any fields
    def sync_to_file(self):
        print "Not implemented"
        return

    pass # class Spec
