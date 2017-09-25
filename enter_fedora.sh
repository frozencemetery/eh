#!/bin/sh

sudo -E sh -c "
mount --bind /proc ${HOME}/fedora/proc
mount --bind /sys ${HOME}/fedora/sys
mount --bind /dev ${HOME}/fedora/dev

exec chroot ${HOME}/fedora/ $*
"
