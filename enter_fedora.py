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

    setup = [c % home for c in [
        "mount --bind /proc %s/fedora/proc",
        "mount --bind /sys %s/fedora/sys",
        "mount --bind /dev %s/fedora/dev",
        "mount --bind /dev/pts %s/fedora/dev/pts",
        "mount --bind /dev/shm %s/fedora/dev/shm",
    ]]

    if not cmd:
        cmd = ""
        pass
    else:
        if type(cmd) != str and type(cmd) != bytes:
            cmd = " ".join(cmd)
            pass
        cmd = "sh -c " + shlex.quote(cmd)
        pass
    chroot = "exec chroot --userspec=%s:%s %s/fedora/ %s" % \
             (user, user, home, cmd)

    script = shlex.quote(";\n".join(setup + [chroot]))
    cmd = "sudo -E sh -c %s" % script
    print(cmd)
    return os.execvp("sudo", shlex.split(cmd))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage a Fedora chroot.")
    parser.add_argument("-u", dest="user", default=os.getuid(),
                        help="user to run commands as inside the chroot")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args(sys.argv[1:])
    exit(chroot(args.user, args.cmd))
