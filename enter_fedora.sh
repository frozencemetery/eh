#!/bin/sh -xe

mount --bind /proc ${HOME}/fedora/proc
mount --bind /sys ${HOME}/fedora/sys
mount --bind /dev ${HOME}/fedora/dev
mount --bind /dev/shm ${HOME}/fedora/dev/shm
mount --bind /dev/pts ${HOME}/fedora/dev/pts

chroot ${HOME}/fedora/ || true

umount ${HOME}/fedora/dev/pts
umount ${HOME}/fedora/dev/shm
umount ${HOME}/fedora/dev
umount ${HOME}/fedora/sys
umount ${HOME}/fedora/proc

