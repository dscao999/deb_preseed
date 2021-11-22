#!/bin/sh -e
#
TARGS=$(getopt -l server:,user:,key:,depot: -o s:u:p:d: -- "$@")
[ $? -ne 0 ] && exit 1
eval set -- $TARGS
export SERVER=
export USER=cloner
export KEY=operation.id
export DEPOT=
while true; do
	case "$1" in
		--server)
			SERVER=$2
			shift
			;;
		--user)
			USER=$2
			shift
			;;
		--key)
			KEY=$2
			shift
			;;
		--depot)
			DEPOT=$2
			shift
			;;
		--)
			shift
			break
			;;
	esac
	shift
done
if [ -z "$DEPOT" -o -z "$SERVER" ]; then
	echo "No clone server and/or directory missing"
	exit 2
fi
#
curdir=${PWD}
srcdir=/mnt
SSHCP="ssh -l ${USER} -i ${curdir}/${KEY} ${SERVER}"
[ ! -d $srcdir ] && mkdir $srcdir
#
# clone LIOS
#
lios_clone()
{
	#
	nparts=$(blkid | fgrep LIOS_ | wc -l)
	if [ ${nparts} -lt 3 ]
	then
		echo "No system to clone. Not a LIOS system?"
		exit 3
	fi
	#
	echo "Clone LIOS into server: $SERVER, directory: $DEPOT ..."
	blkid | fgrep LIOS_ | ${SSHCP} "cat > ${DEPOT}/sys_disk_partitions.txt"
	#
	part1=$(blkid|fgrep LIOS_|cut -d: -f1|head -1)
	suffix=
	blkdev=$(basename $part1)
	[ "$blkdev" != ${blkdev#nvme} -o "$blkdev" != "${blkdev#mmc}" ] && suffix=p
	sysdisk=${part1%${suffix}[0-9]*}
	echo "System disk to clone: $sysdisk"
	cat /sys/block/$(basename $sysdisk)/size | ${SSHCP} "cat > ${DEPOT}/sys_disk_size.txt"
	sfdisk --dump ${sysdisk} | ${SSHCP} "cat > ${DEPOT}/sys_disk_sfdisk.dat"
	pstart="$(sfdisk --dump ${sysdisk}|fgrep ${sysdisk}${suffix}1|sed -e 's/  *//g'|cut -d, -f1|cut -d= -f2)"
	echo "Partition Start Sector: ${pstart}"
	dd if=${sysdisk} bs=512 count=${pstart} | ${SSHCP} "cat > ${DEPOT}/grub_code.dat"
	#
	#  mount and copy file system
	#
	#
	blkid|fgrep LIOS_| while read dp labels
	do
		dpart=${dp%:*}
		echo "Clone $dpart..."
		eval $labels
		[ "$TYPE" = "swap" ] && continue
#
		mount -t $TYPE -o ro $dpart $srcdir
		tsize=$(df -k|fgrep $dpart|sed -e 's/  */:/g'|cut -d: -f3)
		echo "Size: $tsize"
		[ $tsize -gt 1232896 ] && \
		echo "Copying files in $dpart, $tsize KBytes, Please wait for a while..."
		cd $srcdir
		tar -cf - . | ${SSHCP} "cat > ${DEPOT}/sys_disk_${LABEL}.tar"
		cd $curdir
		echo "Umounting $dpart"
		umount $dpart
	done
	#
	echo "LIOS cloned into directory: ${SERVER}${DEPOT}"
}
#
#  set up bootstrap
#
SWAP_LABEL=
SWAP_UUID=
bootstrap_setup()
{
	wget ${URL}/sys_disk_partitions.txt
	rootdev=$(fgrep LIOS_ROOTFS sys_disk_partitions.txt|cut -d: -f1)
	mount $rootdev /mnt
	bootdev=$(fgrep LIOS_BOOTFS sys_disk_partitions.txt|cut -d: -f1)
	mount $bootdev /mnt/boot
	uefidev=$(fgrep LIOS_ESP sys_disk_partitions.txt|cut -d: -f1)
	mount $uefidev /mnt/boot/efi
	mount --rbind /proc /mnt/proc
	mount --rbind /dev  /mnt/dev
	mount --rbind /sys  /mnt/sys
	mount --rbind /run  /mnt/run
	swapdev=$(fgrep LIOS_SWAP sys_disk_partitions.txt|cut -d: -f1)
	eval $(cat /tmp/swap-info.txt)
	chroot /mnt mkswap -L $SWAP_LABEL -U $SWAP_UUID $swapdev
#
	if [ "$UEFIBOOT" -eq 0 ]; then
		echo "Restoring Legacy BIOS boot records"
		dd if=$TARGET bs=512 count=1 of=/tmp/disk_mbr.dat
		wget ${URL}/grub_code.dat
		dd if=grub_code.dat bs=1 count=446 of=/tmp/disk_mbr.dat conv=notrunc
		dd if=/tmp/disk_mbr.dat bs=512 of=$TARGET conv=notrunc
		dd if=grub_code.dat bs=512 skip=1 of=$TARGET seek=1 conv=notrunc
		sync $TARGET
	elif [ $UEFIBOOT -eq 1 ]; then
		echo "Restoring UEFI Boot Records"
		mount -t efivarfs efivarfs /mnt/sys/firmware/efi/efivars
		chroot /mnt efibootmgr|grep -E 'debian|LIOS'|cut -d* -f1|while read bootnum
		do
			bootnum=${bootnum#Boot}
			chroot /mnt efibootmgr -b ${bootnum} -B
		done
		chroot /mnt efibootmgr -c -d $TARGET -p 1 -L "Lenovo LIOS" -l /EFI/debian/shimx64.efi
		umount /mnt/sys/firmware/efi/efivars
	fi
#
	umount /mnt/run
	umount /mnt/sys
	umount /mnt/dev/pts
	umount /mnt/dev
	umount /mnt/proc
	umount /mnt/boot/efi
	umount /mnt/boot
	umount /mnt
}
#
# find the hard disk
#
lsdisk()
{
	numdisks=$(ls -l /sys/block|grep -E 'virtual|total|usb' -v|wc -l)
	if [ $numdisks -gt 1 ]; then
		echo "Number of disks: $numdisks > 1, Cannot restore without user interaction."
		exit 15
	fi
	disk=$(ls -l /sys/block|grep -E 'virtual|usb|total' -v|sed -e 's/  *//g'|cut -d'>' -f2)
	disk=$(basename $disk)
}
#
restore_to()
{
	echo "Will restore from $SERVER:$DEPOT to $TARGET"
	echo "Warning: All data on disk $TARGET will be erased!"
	wget -O - ${URL}/sys_disk_sfdisk.dat|sfdisk $TARGET
	sync
#
	wget -O - ${URL}/sys_disk_partitions.txt | \
	while read diskpart label_info
	do
		device=${diskpart%:*}
		eval $label_info
		echo "Device $device, Type $TYPE, Label $LABEL"
		case $TYPE in
		vfat)
			uuid=${UUID%-*}${UUID#*-}
			mkfs.fat -n $LABEL -F 32 -i $uuid $device
			;;
		swap)
			echo "SWAP_UUID=\"$UUID\" SWAP_LABEL=\"$LABEL\"" > /tmp/swap-info.txt
			;;
		xfs)
			mkfs.xfs -m uuid=$UUID -L $LABEL -f $device
			;;
		ext2)
			mkfs.ext2 -L $LABEL -U $UUID $device
			continue
			;;
		*)
			echo "Unknown file system type: $TYPE"
			continue
			;;
		esac
		[ "$TYPE" = "swap" -o "$TYPE" = "ext2" ] && continue
#
		echo "Restoring contents from $DEPOT/sys_disk_${LABEL}.tar ..."
		mount -t $TYPE $device /mnt
		cd /mnt
		wget -O - ${URL}/sys_disk_${LABEL}.tar | tar -xf -
		cd $curdir
		echo "Umounting $device"
		umount /mnt
	done
	bootstrap_setup
}
#
ecode=9
action=$1
[ -z "$action" ] && action=clone
case "$action" in
	"clone")
		lios_clone
		ecode=$?
		;;
	"restore")
		UEFIBOOT=0
		if ls -ld /sys/firmware/efi; then
			UEFIBOOT=1
		fi
		URL=http://${SERVER}/${DEPOT#/var/www/html/}
		disk=
		lsdisk
		TARGET=/dev/$disk
		TARSIZ=$(cat /sys/block/$disk/size)
		SRCSIZ=$(wget -O - $URL/sys_disk_size.txt)
		if [ $TARSIZ -lt $SRCSIZ ]; then
			echo "Source disk size: $SRCSIZ, Target disk size: $TARSIZ"
			echo "Cannot perform the OS restore"
			exit 19
		fi
		restore_to
		ecode=$?
		;;
	"*")
		echo "Invalid action: $action"
		ecode=9
		;;
esac
exit $ecode
