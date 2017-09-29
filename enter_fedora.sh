#!/bin/sh

sudo -E sh -c "
mount --bind /proc ${HOME}/fedora/proc
mount --bind /sys ${HOME}/fedora/sys
mount --bind /dev ${HOME}/fedora/dev
mount --bind /dev/pts ${HOME}/fedora/dev/pts
mount --bind /dev/shm ${HOME}/fedora/dev/shm

exec chroot ${HOME}/fedora/ $*
"
