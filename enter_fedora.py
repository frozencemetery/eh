#!/usr/bin/python3

import argparse
import os
import shlex
import sys

def chroot(user, cmd=None):
    home = os.getenv("HOME")
    if not home:
        print("go home", file=sys.stderr)
        return -1

    setup = []
    if not os.path.exists(f"{home}/fedora/dev/pts"):
        setup = [f"mount --bind /proc {home}/fedora/proc",
                 f"mount --bind /sys {home}/fedora/sys",
                 f"mount --bind /dev {home}/fedora/dev",
                 f"mount --bind /dev/pts {home}/fedora/dev/pts",
                 f"mount --bind /dev/shm {home}/fedora/dev/shm",
        ]
        pass

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
    return os.execvp("sudo", shlex.split(cmd))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage a Fedora chroot.")
    parser.add_argument("-u", dest="user", default=os.getuid(),
                        help="user to run commands as inside the chroot")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args(sys.argv[1:])
    exit(chroot(args.user, args.cmd))
