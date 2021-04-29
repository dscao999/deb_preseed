#!/bin/bash
#
target_base=/var/www/html/debian
#
srcdir=${PWD}/src-$$
#
if ! sudo ls /etc > /dev/null 2>&1
then
	echo "sudo without password priviledge is required!"
	exit 4
fi
#
# clean up
#
function cleanup()
{
	if mountpoint -q $srcdir
	then
		sudo umount $srcdir
	fi
	[ -d $srcdir ] && rmdir $srcdir
	[ -n "$target_dir" ] && rm -rf $target_dir
}
#
# clone LIOS
#
function lios_clone()
{
	clone_dir=clone-$(date "+%m%d%y-%H%M")
	target_dir=$target_base/$clone_dir
	#
	sudo blkid | fgrep LIOS_ > /tmp/sys_disk_partitions.txt
	parts=$(awk -F": " '{print $1}' /tmp/sys_disk_partitions.txt)
	if [ ${#parts} -eq 0 ]
	then
		echo "No system to clone. Not a LIOS system?"
		rm /tmp/sys_disk_partitions.txt
		exit 1
	fi
	#
	echo "Clone LIOS into directory: $target_dir ..."
	[ -d $target_dir ] && rm -rf $target_dir
	mkdir $target_dir
	cp /tmp/sys_disk_partitions.txt $target_dir/sys_disk_partitions.txt
	rm /tmp/sys_disk_partitions.txt
	#
	sysdisk=${parts[0]%%[0-9]*}
	echo "System disk to clone: $sysdisk"
	cat /sys/block/$(basename $sysdisk)/size > $target_dir/sys_disk_size.txt
	sudo sfdisk --dump ${sysdisk} | cat > $target_dir/sys_disk_sfdisk.dat
	pstart=$(fgrep ${sysdisk}1 $target_dir/sys_disk_sfdisk.dat|awk '{print $4}')
	pstart=${pstart%,}
	echo "Partition Start Sector: ${pstart}"
	sudo dd if=${sysdisk} bs=512 count=$pstart | cat > $target_dir/grub_code.dat
	#
	#  mount and copy file system
	#
	#
	trap cleanup INT
	#
	[ -d $srcdir ] || mkdir $srcdir
	for dpart in ${parts[@]}
	do
		echo "Partiton: $dpart"
		info_line="$(fgrep $dpart $target_dir/sys_disk_partitions.txt)"
		for keyval in $info_line
		do
			key=${keyval%%=*}
			if [ "$key" = "LABEL" ]
			then
				eval $keyval
			elif [ "$key" = "TYPE" ]
			then
				eval $keyval
			fi
		done
#
		[ "$LABEL" = "LIOS_SWAP" ] && continue
		sudo mount -t $TYPE -o ro $dpart $srcdir
		tsize=$(df -k | fgrep $dpart | awk '{print $3}')
		echo "Size: $tsize"
		[ $tsize -gt 1232896 ] && \
		echo "Copying files in $dpart, $tsize KBytes, Please wait for a while..."
		pushd $srcdir
		sudo find . -print | sudo cpio -o | \
			dd of=$target_dir/sys_disk_${LABEL}.cpio obs=128K
		popd
		sudo umount $dpart
	done
	rmdir $srcdir
	#
	sudo sync
	echo "LIOS cloned into directory: $target_dir"
}
function restore_to()
{
	local source target

	source=$1
	target=$2
	echo "Warning: All data on disk $target will be erased!"
	read -p "Continue?[Y]" confirm
	[ "x$confirm" != "xY" ] && return
	echo "Will restore from $source to $target"
}
#
# restore LIOS
#
function lios_restore()
{
	local source dadisks

	source=$1
	dadisks=($(ls -l /sys/block|fgrep -v usb|fgrep -v virtual| \
		grep -E '^l'|awk '{print $9}'))
	echo "Please select the disk to restore to: "
	select disk in ${dadisks[@]}
	do
		if [ -z "$disk" ]
		then
			echo "No disk selected."
			break
		fi
		echo "Will use disk $disk as restore target. "
		restore_to $source /dev/$disk
		break
	done
}
#
action=$1
[ -z "$action" ] && action=clone
case "$action" in
	"clone")
		lios_clone
		ecode=$?
		;;
	"restore")
		images=$(ls -ldtr $target_base/clone-*|awk '{print $9}')
		if [ ${#images[@]} -eq 0 ]
		then
			echo "No Clone Images to use."
			exit 3
		fi
		echo "Please select the resotre image: "
		select from in ${images[@]}
		do
			[ -z "$from" ] && continue
			echo "Will use image $from as restore source. "
			read -p "Continue?[Y] " ack
			[ "x$ack" != "xY" ] && break
			lios_restore $from
			break
		done
		ecode=$?
		;;
	"*")
		echo "Invalid action: $action"
		ecode=9
		;;
esac
#
exit $ecode
