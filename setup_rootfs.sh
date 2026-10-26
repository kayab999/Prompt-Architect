#!/bin/bash
set -e
# Create minimal rootfs
dd if=/dev/zero of=firecracker_images/rootfs.ext4 bs=1M count=64
mkfs.ext4 -F firecracker_images/rootfs.ext4

# Mount
mkdir -p /tmp/rootfs
sudo mount -o loop firecracker_images/rootfs.ext4 /tmp/rootfs

# Build Busybox structure
sudo mkdir -p /tmp/rootfs/{bin,sbin,etc,proc,sys,dev,mnt}
# Use static busybox if possible, or copy from host
# (Assuming host has busybox for now)
if [ -f /bin/busybox ]; then
    sudo cp /bin/busybox /tmp/rootfs/bin/
else
    # Fallback to a simple static binary if needed
    echo "Busybox not found at /bin/busybox"
    exit 1
fi

# Link everything
sudo /tmp/rootfs/bin/busybox --install -s /tmp/rootfs/bin

# Install immutable init
sudo cp buildroot_config/buildroot-2024.02/board/prompt_architect/overlay/sbin/init /tmp/rootfs/sbin/init
sudo chmod +x /tmp/rootfs/sbin/init

# Cleanup
sudo umount /tmp/rootfs
rmdir /tmp/rootfs
