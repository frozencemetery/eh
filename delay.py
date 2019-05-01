#!/usr/bin/env python3

import argparse
import json
import requests
import time

def wait_gate(pkg):
    params = {
        "topic": "/topic/VirtualTopic.eng.greenwave.decision.update",
        "rows_per_page": "1",
        "package": pkg
    }
    url = "https://datagrepper.engineering.redhat.com/raw"

    last_summary = ""
    while True:
        time.sleep(1)
        r = requests.get(url, params=params)
        if r.status_code != 200:
            print(f"Problematic datagrepper request: got a {r.status_code}")
            exit(-1)

        j = json.loads(r.text)
        summary = j["raw_messages"][0]["msg"]["summary"]
        if summary == "All required tests passed":
            break
        elif "failed" in summary:
            print(f"Died in gating: {summary}")
            exit(-1)
        elif summary != last_summary:
            last_summary = summary
            print(f"Gating status update: {summary}")
        continue

    print("Passed gating (woo!)")
    return

def verify(args):
    if not args.pkg:
        print("Need to specify a single package!")
        exit(1)
    return args

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wait on a package's event.")
    parser.add_argument("-g", dest="gate", action="store_true",
                        help="wait for gating to finish")
    parser.add_argument("pkg", default=None, nargs='?')
    args = parser.parse_args()
    args = verify(args)

    if args.gate:
        wait_gate(args.pkg)
        pass

    exit(0)
