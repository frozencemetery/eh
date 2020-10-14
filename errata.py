#!/usr/bin/env python3

# for requests_gssapi
import os
import sys

import json
import re
import requests


from requests_gssapi import HTTPSPNEGOAuth # type: ignore

from typing import Any, Dict, Optional

# sessions enable keepalive
s = requests.Session()

BASE = "https://errata.devel.redhat.com/"

def get(slug: str) -> Any:
    r = s.get(f"{BASE}/{slug}", auth=HTTPSPNEGOAuth())
    if not r.ok:
        print(f"Errata: got {r.status_code}\n{r.text}")

    return r.json()

def post(slug: str, payload: Dict[str, Any]) -> Optional[Any]:
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    r = s.post(f"{BASE}/{slug}", data=json.dumps(payload),
               auth=HTTPSPNEGOAuth(), headers=headers)
    if not r.ok:
        print(f"Errata: got {r.status_code}\n{r.text}")
        return r.json()

    return None

def find_errata(component: str, release: str) -> Optional[str]:
    erratas = get("filter/3.json") # "Active, reported by you"
    for errata in erratas:
        pkg = errata["synopsis"].split(" ", 1)[0]
        if errata["release"]["name"] != release or pkg != component:
            continue
        return str(errata["id"])

    return None

class Erratum:
    eid: str

    def set_state(self, state: str) -> Optional[Any]:
        print(f"Setting state to {state}")
        return post(f"api/v1/erratum/{self.eid}/change_state",
                    {"new_state": state})

    # We might be able to forgo pv here with some caching
    def add_build(self, pv: str, nvr: str) -> Optional[Any]:
        assert(not self.set_state("NEW_FILES"))
        print("Adding build...")
        payload = {
            "product_version": pv,
            "nvr": nvr,
        }
        return post(f"api/v1/erratum/{self.eid}/add_build", payload)

    # We might be able to determine errata state in advance here
    def add_bug(self, bz: str) -> Optional[Any]:
        assert(not self.set_state("NEW_FILES"))
        print("Adding bug...")
        return post(f"api/v1/erratum/{self.eid}/add_bug", {"bug": bz})

    def __init__(self, component: str, release: str,
                 bz: Optional[str] = None) -> None:
        print("Looking for errata...")

        leid = find_errata(component, release)
        if leid:
            self.eid = leid
            print(f"Has errata {self.eid}")
            if not bz:
                return
            return self.add_bug(bz)

        if not bz:
            print("Bugzilla needed to create errata!")
            exit(1)

        adv = {
            "advisory": {
                "errata_type": "RHBA",
                "security_impact": "None",
                "solution": "Before applying this update, make sure all previously released errata\nrelevant to your system have been applied.\n\nFor details on how to apply this update, refer to:\n\nhttps://access.redhat.com/articles/11258", # noqa: E501
                "description": f"Bugfix update for {component}",
                "manager_email": "mkosek@redhat.com",
                "package_owner_email": "rharwood@redhat.com",
                "synopsis": f"{component} bug fix and enhancement update",
                "topic": f"Updated {component} packages that fix several bugs and add various enhancements are now available.", # noqa: E501
                "idsfixed": bz,
                "quality_responsibility_name": "IdM - Enterprise Identity Management", # noqa: E501
            },
            "product": "RHEL",
            "release": release,
        }
        res = post("api/v1/erratum/", adv)
        assert(not res)
        leid = find_errata(component, release)
        assert(leid)
        self.eid = leid
        print(f"Has errata {self.eid}")
        return

def usage(name: str) -> int:
    print(f"Usage: {name} PKG in RELEASE add_bug BZ\n"
          f"  or:  {name} PKG in RELEASE add_build NVR\n"
          f"  or:  {name} PKG in RELEASE set_state STATE")
    return 1

if __name__ == "__main__":
    try:
        name = sys.argv[0]
        pkg = sys.argv[1]
        if sys.argv[2] != "in":
            exit(usage(name))

        m = re.search(r"\d.\d", sys.argv[3])
        if not m:
            exit(usage(name))
        release = f"RHEL-{m.group(0)}.0.GA"

        verb = sys.argv[4]
        arg = sys.argv[5]
    except IndexError:
        exit(usage(name))

    if verb == "add_bug":
        e = Erratum(pkg, release, arg)
        exit(not e)
    elif verb == "add_build":
        e = Erratum(pkg, release)
        exit(e.add_build(release, arg))
    elif verb == "set_state":
        e = Erratum(pkg, release)
        exit(e.set_state(arg))
    else:
        exit(usage(name))
