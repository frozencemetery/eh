#!/usr/bin/python3

import argparse
import fcntl
import os
import shlex
import subprocess
import sys

def chroot(cmd=None, user=None):
    if not user:
        user = os.getuid()
        pass

    home = os.getenv("HOME")
    if not home:
        print("go home", file=sys.stderr)
        return -1

    lockfile = open(f"{home}/.chrootlock", "a")
    try:
        fcntl.lockf(lockfile, fcntl.LOCK_EX)
        lockfile.write(f"{os.getpid()}\n")
        lockfile.flush()
        pass
    except Exception:
        print(f"Already locked by {lockfile.read()}")
        exit(-1)

    setup = []
    if not os.path.exists(f"{home}/fedora/dev/shm"):
        setup = [
            f"mount -t proc none {home}/fedora/proc",
            f"mount --bind /sys {home}/fedora/sys",
            f"mount --bind /dev {home}/fedora/dev",
            f"mount --bind /dev/pts {home}/fedora/dev/pts",
            f"mount --bind /dev/shm {home}/fedora/dev/shm",
        ]
        pass
    fcntl.lockf(lockfile, fcntl.LOCK_UN)

    if not cmd:
        cmd = ""
        pass
    else:
        if type(cmd) != str and type(cmd) != bytes:
            cmd = " ".join(cmd)
            pass
        cmd = "sh -c " + shlex.quote(cmd)
        pass
    chroot = f"exec chroot --userspec={user}:{user} {home}/fedora/ {cmd}"

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
