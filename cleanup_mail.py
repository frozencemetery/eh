#!/usr/bin/env python2

import re
import sys

def unesc(s):
    sl = list(s)

    i = 0
    while i < len(sl):
        if sl[i] == '%':
            c1 = sl[i + 1]
            c2 = sl[i + 2]
            c = chr(int(c1 + c2, 16))
            sl[i] = c

            # order matters here
            del(sl[i + 2])
            del(sl[i + 1])
            pass

        i += 1
        pass
    return ''.join(sl)

s = sys.stdin.read()

m = re.match(
    "\<a href=\"mailto:(.*?@.*?)\?body=(.*?)&amp;subject=(.*?)\"\>.*\</a\>",
    s)

mailto = m.group(1)
body = unesc(m.group(2))
subject = unesc(m.group(3))

print "From: Robbie Harwood <rharwood@redhat.com>"
print "To: %s" % mailto
print "Subject: %s" % subject
print "Fcc: sent"
print "--text follows this line--"
print "<#secure method=pgpmime mode=sign>"
print "%s" % body
print ""
