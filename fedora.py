#!/usr/bin/python3

import argparse
import fcntl
import os
import shlex
import subprocess
import sys

def chroot(cmd=None, user=None):
    user = user if user else os.getuid()

    if not cmd:
        shell = os.getenv("SHELL", "sh")
        cmd = f"{shell} -i"
    if type(cmd) != str and type(cmd) != bytes:
        cmd = " ".join(cmd)

    home = os.getenv("HOME")
    if not home:
        print("go home", file=sys.stderr)
        return -1
    home = os.path.realpath(home)

    # If we're in a subdir of the chroot, continue being there.  Otherwise,
    # start at ~ inside the chroot.
    fedora = os.path.join(home, "fedora")
    pwd = os.getcwd()
    pwd = pwd[len(fedora):] if fedora in pwd else ""
    cmd = f"cd {pwd}; {cmd}"

    lockfile = open(f"{home}/.chrootlock", "a")
    try:
        fcntl.lockf(lockfile, fcntl.LOCK_EX)
        lockfile.write(f"{os.getpid()}\n")
        lockfile.flush()
    except Exception:
        print(f"Already locked by {lockfile.read()}")
        exit(-1)

    setup = []
    if not os.path.exists(f"{fedora}/dev/shm"):
        setup = [
            f"mount -t proc none {fedora}/proc",
            f"mount --bind /sys {fedora}/sys",
            f"mount --bind /dev {fedora}/dev",
            f"mount --bind /dev/pts {fedora}/dev/pts",
            f"mount --bind /dev/shm {fedora}/dev/shm",
        ]
    fcntl.lockf(lockfile, fcntl.LOCK_UN)

    cmd = "sh -c " + shlex.quote(cmd)
    chroot = f"exec chroot --userspec={user}:{user} {fedora}/ {cmd}"

    script = shlex.quote(";\n".join(setup + [chroot]))
    cmd = f"sudo -E sh -c {script}"
    return subprocess.call(shlex.split(cmd))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage a Fedora chroot.")
    parser.add_argument("-u", dest="user", default=os.getuid(),
                        help="user to run commands as inside the chroot")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args(sys.argv[1:])
    exit(chroot(args.cmd, args.user))
