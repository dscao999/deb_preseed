#!/bin/sh
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
srcdir=/mntsrc
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
bootstrap_setup()
{
	local srcpath target mbrf

	srcpath=$1
	target=$2
	mbrf=$(basename $target)
	eval $(blkid $target | cut -d: -f2)
	if [ "$PTTYPE" == "dos" ]
	then
		dd if=$target bs=512 count=1 | cat > /tmp/${mbrf}_mbr.dat
		dd if=$srcpath/grub_code.dat bs=1 count=446 of=/tmp/${mbrf}_mbr.dat \
			conv=notrunc,nocreat
		dd if=/tmp/${mbrf}_mbr.dat bs=512 of=$target oflag=direct \
			conv=nocreat,notrunc
		dd if=$srcpath/grub_code.dat bs=512 skip=1 of=$target seek=1 \
			oflag=direct conv=nocreat,notrunc
	fi
	if [ $UEFIBOOT -eq 1 ] && ls -ld /sys/firmware/efi > /dev/null 2>&1
	then
		efibootmgr -c -d $target -p 1 -L "LIOS" -l '\EFI\debian\shimx64.efi'
	fi
}
#
restore_to()
{
	local srcpath target device odevice

	srcpath=$1
	target=$2
	echo "Warning: All data on disk $target will be erased!"
	read -p "Continue?[N]" confirm
	[ "x$confirm" != "xY" ] && return
	echo "Will restore from $srcpath to $target"
	tweak_sfdisk
	./tweak_sfdisk.py $target $srcpath /tmp/sys_disk_sfdisk.dat /tmp/sys_disk_partitions.txt
	rm tweak_sfdisk.py
	sfdisk $target < /tmp/sys_disk_sfdisk.dat
	sync
#
	while read diskpart label_info
	do
		device=${diskpart%:*}
		eval $label_info
		echo "Device $device, Type $TYPE, Label $LABEL"
		case $TYPE in
		vfat)
			uuid=${UUID%-*}${UUID#*-}
			mkfs -t $TYPE -n $LABEL -F 32 -i $uuid $device
			;;
		swap)
			mkswap -L $LABEL -U $UUID $device
			;;
		xfs)
			mkfs -t $TYPE -m uuid=$UUID -L $LABEL -f $device
			;;
		ext2)
			mkfs -t $TYPE -L $LABEL -U $UUID $device
			continue
			;;
		*)
			echo "Unknown file system type: $TYPE"
			continue
			;;
		esac
		[ "$TYPE" = "swap" -o "$TYPE" = "ext2" ] && continue
#
		fin=0
		dots=0
		{
			mount -t $TYPE $device /mnt
			pushd /mnt
			echo "Restoring contents from $srcpath/sys_disk_${LABEL}.cpio ..."
			cpio --block-size=256 -id < $srcpath/sys_disk_${LABEL}.cpio
			[ "$LABEL" = "LIOS_ESP" -a -f EFI/debian/shimx64.efi ] && \
				UEFIBOOT=1
			popd
			echo "Umounting $device"
			umount /mnt
		}
	done < /tmp/sys_disk_partitions.txt
	bootstrap_setup $srcpath $target
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
		echo "Please select the resotre image: "
		ecode=$?
		;;
	"*")
		echo "Invalid action: $action"
		ecode=9
		;;
esac
exit $ecode
