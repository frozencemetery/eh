#!/usr/bin/env python3

import argparse
import os
import subprocess

def runex(cmd: str, new: bool = True, path: str = ".") -> None:
    if not new and os.path.exists(path):
        return

    print(f"+{cmd}")
    try:
        subprocess.check_call([cmd], shell=True)
    except subprocess.CalledProcessError:
        exit(-1)

def verify(args: argparse.Namespace) -> argparse.Namespace:
    if args.clang and args.gcc:
        print("ERROR: clang and gcc are mutually exclusive")
        exit(1)
    args.c_compiler = "clang" if args.clang else "gcc"

    args.path = os.path.abspath(args.path)

    comps = args.path.split('/')
    while not comps[-1].endswith(".git"):
        del(comps[-1])
    if len(comps) == 0:
        print("ERROR: couldn't detect project name (no projectname.git)")
        exit(1)
    args.project = comps[-1][:-len(".git")]

    return args

def get_configure_flags(project: str) -> str:
    if project == "krb5":
        return "--with-ldap"
    return ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Try to build, using heuiristics and hacks.")
    parser.add_argument("-c", dest="clang", action="store_true", default=True,
                        help="Force use of clang (default: yes)")
    parser.add_argument("-g", dest="gcc", action="store_true",
                        help="Force use of gcc (default: no)")
    parser.add_argument("-n", dest="new", action="store_true",
                        help="Do a full new build (default: no)")
    parser.add_argument("path", nargs='?', default=".",
                        help="where to build (default: cwd)")
    args = parser.parse_args()
    args = verify(args)
    print("Everything looks okay; let's go...")

    ls = os.listdir(args.path)
    if "configure.ac" not in ls and "src" in ls:
        args.path += "/src"

    os.chdir(args.path)

    if args.new:
        print(subprocess.getoutput("git clean -xdf"))

    cflags = "-O0 -ggdb -fPIE -fPIC -Wl,-z,relro"
    runex("autoreconf -fiv", args.new, "configure")
    runex(f"./configure CC=$(which {args.c_compiler}) "
          f"CFLAGS='{cflags}' {get_configure_flags(args.project)}",
          args.new, "Makefile")
    runex(f"make -sj8 >/dev/null")
    runex(f"make check")
