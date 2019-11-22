#!/usr/bin/env python3

import argparse
import json
import requests
import time

from bs4 import BeautifulSoup

# This entire setup assumes that only one instance of a particular package is
# in the pipeline at any time.  I may have to correct this later, but let's
# not let the perfect be the enemy of the good here.

def _get_json(package, topic):
    params = {
        "package": package,
        "topic": f"/topic/VirtualTopic.eng.{topic}",
        "rows_per_page": "1",
    }
    url = "https://datagrepper.engineering.redhat.com/raw"
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"Problematic datagrepper request: got a {r.status_code}")
        exit(-1)

    return json.loads(r.text)

def wait_gate(pkg):
    last_summary = ""
    while True:
        time.sleep(1)
        j = _get_json(pkg, "greenwave.decision.update")
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

def wait_rpmdiff(pkg):
    # Heuristic: it won't pass immediately.  So let's get the ID out of the
    # first message we have, and then wait for a new one.

    j = _get_json(pkg, "rpmdiff.job.completed")
    prev_id = cur_id = j["raw_messages"][0]["headers"]["run_id"]
    while prev_id == cur_id:
        time.sleep(1)
        j = _get_json(pkg, "rpmdiff.job.completed")
        cur_id = j["raw_messages"][0]["headers"]["run_id"]
        pass

    status = j["raw_messages"][0]["msg"]["overall_score"]
    if status in ["Passed", "Info"]:
        # Info means Passed; Passed is hypothetical
        print("Passed rpmdiff on the first try!  You go, Glen Coco!")
        return

    print(f"rpmdiff failed with: {status}")

    print("Waiting for you to waive: \a") # ring bell
    print(f"https://rpmdiff.engineering.redhat.com/run/{cur_id}")

    # Now wait for it to get waived
    this_id = ""
    while cur_id != this_id:
        time.sleep(1)
        j = _get_json(pkg, "rpmdiff.job.waived")
        this_id = j["raw_messages"][0]["headers"]["run_id"]
        pass
    return

def _get_cov(pkg):
    base = "https://cov01.lab.eng.brq.redhat.com"
    r = requests.get(f"{base}/covscanhub/waiving?search={pkg}")
    if r.status_code != 200:
        print(f"Problematic covscan request: got a {r.status_code}")
        exit(-1)

    # Beautiful.  Right.
    soup = BeautifulSoup(r.text, "lxml")
    tds = soup.find_all("tr")[1].find_all("td")
    status = tds[3].next.strip()
    slug = tds[0].a["href"]
    return status, f"{base}/{slug}"

def wait_covscan(pkg):
    # Heuristic: it's the latest run.  It wouldn't be too hard to get smarter
    # about this.

    while True:
        status, url = _get_cov(pkg)
        if status in ["BASE_SCANNING", "SCANNING"]:
            continue
        elif status == "PASSED":
            print("Passed covscan!  Something must be very wrong...")
            return
        elif status == "FAILED":
            print("Failed covscan.  Time to run cleanup_mail...")
            exit(-1)
        elif status == "NEEDS_INSPECTION":
            print("\a") # attention
            print(f"Please take a look at {url}")
            break
        print(f"Unknown covscan status in first pass: {status}")
        exit(-1)

    while True:
        status, _ = _get_cov(pkg)
        if status in ["PASSED", "WAIVED", "BUG_CONFIRMED"]:
            break
        continue
    print("covscan complete!")
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
    parser.add_argument("-r", dest="rpmdiff", action="store_true",
                        help="wait for rpmdiff to finish")
    parser.add_argument("-c", dest="covscan", action="store_true",
                        help="wait for covscan to finish")
    parser.add_argument("pkg", default=None, nargs='?')
    args = parser.parse_args()
    args = verify(args)

    if args.gate:
        wait_gate(args.pkg)
        pass

    if args.rpmdiff:
        wait_rpmdiff(args.pkg)
        pass

    if args.covscan:
        wait_covscan(args.pkg)

    exit(0)
