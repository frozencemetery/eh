#!/bin/sh -xe

sudo -E sh -ex <<EOF
    mount --bind /proc ~/fedora/proc
    mount --bind /sys ~/fedora/sys
    mount --bind /dev ~/fedora/dev
    mount --bind /dev/shm ~/fedora/dev/shm
    mount --bind /dev/pts ~/fedora/dev/pts

    chroot ~/fedora/ || true

    umount ~/fedora/dev/pts
    umount ~/fedora/dev/shm
    umount ~/fedora/dev
    umount ~/fedora/sys
    umount ~/fedora/proc
EOF
