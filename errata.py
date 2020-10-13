import json
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

    def add_bug(self, bz: str) -> Optional[Any]:
        print("Adding bug...")
        return post(f"api/v1/erratum/{self.eid}/add_bug", {"bug": bz})

    def add_build(self, pv: str, nvr: str) -> Optional[Any]:
        print("Adding build...")
        payload = {
            "product_version": pv,
            "nvr": nvr,
        }
        return post(f"api/v1/erratum/{self.eid}/add_build", payload)

    def set_state(self, state: str) -> Optional[Any]:
        print(f"Setting state to {state}")
        return post(f"api/v1/erratum/{self.eid}/change_state",
                    {"new_state": state})

    def __init__(self, component: str, release: str, bz: str) -> None:
        print("Looking for errata...")

        leid = find_errata(component, release)
        if leid:
            self.eid = leid
            print(f"Has errata {self.eid}")
            self.add_bug(bz)
            return

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
        print(res)
        leid = find_errata(component, release)
        assert(leid)
        self.eid = leid
        print(f"Has errata {self.eid}")
        return
