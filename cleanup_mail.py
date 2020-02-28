#!/usr/bin/env python3

import re
import sys

from bs4 import BeautifulSoup # type: ignore

def unesc(s: str) -> str:
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

        i += 1

    return ''.join(sl)

s = sys.stdin.read()
soup = BeautifulSoup(s, "lxml")
[link] = soup.find_all("a", text="this pre-populated mailto link")
href = link.attrs["href"]

# The order of parameters on this link isn't fixed
m = re.search(r"mailto:(.*?@.*?)\?", href)
assert(m)
mailto = unesc(m.group(1))

m = re.search("subject=([^&]*)", href)
assert(m)
subject = unesc(m.group(1))

m = re.search("body=([^&]*)", href)
assert(m)
body = unesc(m.group(1))

print("From: Robbie Harwood <rharwood@redhat.com>")
print("To: %s" % mailto)
print("Subject: %s" % subject)
print("Fcc: sent")
print("--text follows this line--")
print("<#secure method=pgpmime mode=sign>")
print("%s" % body)
print("")
