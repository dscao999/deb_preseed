#!/bin/bash
#
if ! sudo ls /etc > /dev/null 2>&1
then
	echo "sudo failed. sudo without password is required for this operation."
fi
#
device=$1
#
function check_usbdisk()
{
	local dev bdev devpath mounted

	dev=$1
	if [ -z "$dev" ]
	then
		echo "Please specify a UDisk device."
		exit 5
	fi
	if [ ! -b $dev ]
	then
		echo "Device $dev is not a block device"
		exit 1
	fi
	bdev=$(basename ${dev})
	devpath=$(ls -l /sys/block|fgrep $bdev|fgrep usb)
	if [ -z "$devpath" ]
	then
		echo "Device $dev is not a USB block device"
		exit 2
	fi
	mounted=$(mount | fgrep $dev)
	if [ -n "$mounted" ]
	then
		echo "Please umount file systems on deivce $dev"
		exit 3
	fi
}
#
cdmedium=/run/live/medium
if ! mountpoint -q $cdmedium
then
	echo "Fata Error: /run/live/medium is not a mount point."
	echo "Not a debian live OS?"
	exit 7
fi
#
check_usbdisk $device
devnam=$(basename $device)
#
disksize=$(($(cat /sys/block/${devnam}/size)/2))
remsize=$(($disksize-4326400))
echo "disksize: $disksize K, remsize: $remsize K"
sudo dd if=/dev/zero of=$device bs=512 count=1
sudo sfdisk --wipe always $device <<-EOD

label: dos

start=1024KiB	size=131072KiB	bootable	type=0x0c
		size=4194304KiB	type=0x83
		size=${remsize}KiB	type=0x83
EOD
sleep 1
sudo sync
#
#  umount /mnt if interrupted
#
function cleanup()
{
	if mountpoint -q /mnt
	then
		sudo umount /mnt
	fi
	[ -d legacy-bios ] && rm -r legacy-bios
	[ -f mbr.dat ] && rm mbr.dat
}
#
trap cleanup EXIT INT
#
sudo blockdev --rereadpt $device
sudo mkfs.vfat -F 32 -n ESPFS ${device}1
sudo mkfs.ext3 -F -L BOOTFS ${device}2
sudo mkfs -t xfs -f -L DEBIAN_DEPOT ${device}3
#
sudo mount ${device}1 /mnt
pushd ${cdmedium}
find ./EFI -print | sudo cpio -pd /mnt
popd
sudo umount /mnt
#
sudo mount ${device}2 /mnt
pushd ${cdmedium}
echo -n "Copying Live OS ..."
find . -print | sudo cpio -pd /mnt
echo
popd
echo -n "Umounting U Disk, will take several minutes..."
sudo umount /mnt
echo
#
sudo mount ${device}3 /mnt
sudo chown 1000:1000 /mnt
sudo umount /mnt
#
# setup legacy bios boot code
#
function setup_legacy()
{
	sudo dd if=${device} of=mbr.dat bs=512 count=1
	sudo dd if=legacy-bios/mbr-boot-code.dat of=mbr.dat bs=1 conv=notrunc
	sudo dd if=mbr.dat of=${device} bs=512 count=1 conv=nocreat oflag=direct
	sudo dd if=legacy-bios/grub-boot-code.dat of=${device} bs=512 seek=1 oflag=direct conv=nocreat
}
lineno=121
tail --lines=+${lineno} ${0} | cpio -id
touch mbr.dat
setup_legacy
rm -rf legacy-bios mbr.dat
#
exit 0
