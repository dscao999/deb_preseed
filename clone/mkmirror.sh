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
biosdat=first-1024K.dat
#
#  umount /mnt if interrupted
#
function cleanup()
{
	if mountpoint -q /mnt
	then
		sudo umount /mnt
	fi
	[ -f $biosdat ] && rm $biosdat
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
find ./EFI -print | sudo cpio --block-size=256 -pd /mnt
popd
sudo umount /mnt
#
sudo mount ${device}2 /mnt
pushd ${cdmedium}
echo -n "Copying Live OS ..."
find . -print | sudo cpio --block-size=256 -pd /mnt
echo
popd
echo -n "Umounting U Disk, will take several minutes..."
sudo umount /mnt
echo
#
sudo mount ${device}3 /mnt
sudo chown 1000:1000 /mnt
cursize=$(df -k | fgrep /var/www/html/debian | awk '{print $3}')
cursize=$((cursize+128))
dstsize=$(df -k | fgrep /mnt | awk '{print $4}')
if [ $cursize -gt 1048576 -a $dstsize -gt $cursize ]
then
	read -p "Would you like copy current debian packages?($((cursize/1048576))G) " ans
	if [ x"$ans" == "xy" -o x"$ans" == "xY" ]
	then
		echo -n "Copying $cursize K Bytes, Please be patient..."
		( cd /var/www/html/debian && find . -print | cpio --block-size=256 -pd /mnt )
		echo "Complete"
	fi

fi
#
echo -n "Unmounting /mnt ..."
sudo umount /mnt
echo ""
#
# setup legacy bios boot code
#
function setup_legacy()
{
	sudo dd if=${device} of=mbr.dat bs=512 count=1
	sudo dd if=$biosdat of=mbr.dat bs=1 count=446 conv=notrunc
	sudo dd if=mbr.dat of=${device} bs=512 count=1 conv=nocreat oflag=direct
	sudo dd if=$biosdat of=${device} bs=512 skip=1 seek=1 oflag=direct conv=nocreat
}
lineno=140
tail --lines=+${lineno} ${0} > $biosdat
touch mbr.dat
setup_legacy
rm -f $biosdat mbr.dat
#
exit 0
