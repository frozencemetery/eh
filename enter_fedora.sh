#!/bin/sh -xe

mount --bind /proc /home/bos/rharwood/fedora/proc
mount --bind /sys /home/bos/rharwood/fedora/sys
mount --bind /dev /home/bos/rharwood/fedora/dev
mount --bind /dev/shm /home/bos/rharwood/fedora/dev/shm
mount --bind /dev/pts /home/bos/rharwood/fedora/dev/pts

chroot /home/bos/rharwood/fedora/ || true

umount /home/bos/rharwood/fedora/dev/pts
umount /home/bos/rharwood/fedora/dev/shm
umount /home/bos/rharwood/fedora/dev
umount /home/bos/rharwood/fedora/sys
umount /home/bos/rharwood/fedora/proc
