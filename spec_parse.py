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
#
# currently tracked:
#  - changelog
#  - release
#  - prep
#  - build
class Spec:
    def __init__(self, path):
        self.path = path
        with open(path, "r") as f:
            self.data = f.read()
            pass

        # changelog macros don't matter, so pull it out first
        rest, _, self._changelog = self.data.partition("%changelog\n")
        # now it is safe to go through the file in either order, so I do it
        # backward because it makes most sense to me

        # tosses out everything after %install / %check
        rest, _, _ = rest.rpartition("%install\n")
        rest, _, whoops = rest.rpartition("%check\n")
        if rest == "":
            # no %check section
            rest = whoops
            pass
        rest, _, self._build = rest.rpartition("%build\n")
        rest, _, self._prep = rest.rpartition("%prep\n")

        # tosses out all descriptions and stuff
        rest, _, _ = rest.rpartition("%description")
        self._release = re.search("\n(Release:\s*.*)\n", rest).group(1)

        # keep track of numbering and such here
        patches = re.findall("Patch\d+:\s*[a-zA-Z0-9_.-]+", rest)
        if len(patches) != 0:
            startind = self.data.index(patches[0])
            endind = self.data.index(patches[-1]) + len(patches[-1])
            self._patches = self.data[startind:endind]
            pass
        self.patches = patches

        # %prep extraction is important for patching
        self._preamble, _, rest = self.data.partition("%description\n")
        self._pkgdata, _, rest = rest.partition("%prep\n")
        self._prep, _, rest = rest.partition("%build\n")
        self._build, _, rest = rest.partition("\n")

        # export (non-patches) fields we support changes to
        self.changelog = self._changelog
        self.release = self._release
        self.prep = self._prep
        self.build = self._build
        return

    # Will not delete any fields.
    def sync_to_file(self):
        self.data = self.data.replace("%changelog\n%s" % self._changelog,
                                      "%changelog\n%s" % self.changelog)
        self._changelog = self.changelog

        self.data = self.data.replace("\nRelease: %s\n" % self._release,
                                      "\nRelease: %s\n" % self.release)
        self._release = self.release

        self.data = self.data.replace("%prep\n%s" % self._prep,
                                      "%prep\n%s" % self.prep)
        self._prep = self.prep

        self.data = self.data.replace("%build\n%s" % self._build,
                                      "%build\n%s" % self.build)
        self._build = self.build

        self.data = self.data.replace(self._patches, "\n".join(self.patches))
        self._patches = "\n".join(self.patches)

        with open(self.path, "w") as f:
            f.write(self.data)
            pass
        return

    pass # class Spec
