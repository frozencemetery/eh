#!/usr/bin/env python3

import argparse
import os
import subprocess

def verify(args):
    if "/" not in args.name:
        print("Malformed name!  Should be: org/proj")
        exit(1)

    temp = args.name.split("/")
    if len(temp) != 2:
        print("Too many slashes in name!  Should be only one.")
        exit(1)

    args.org = temp[0]
    args.proj = temp[1]
    return args

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Set up a new project.")
    parser.add_argument("name", help="Project name (in the form: org/proj)")
    args = parser.parse_args()
    args = verify(args)

    os.chdir(os.getenv("HOME"))

    gitdir = f"{args.proj}.git"
    os.mkdir(gitdir)
    os.chdir(gitdir)

    subprocess.check_call(f"git clone git@github.com:{args.name} master",
                          shell=True)
    print(f"All set to go in ~/{args.proj}.git")
    exit(0)
