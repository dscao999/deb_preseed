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
	parts=($(awk -F": " '{print $1}' /tmp/sys_disk_partitions.txt))
	if [ ${#parts[@]} -lt 3 ]
	then
		echo "No system to clone. Not a LIOS system?"
		rm /tmp/sys_disk_partitions.txt
		cleanup
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
	while read dp labels
	do
		dpart=${dp%:*}
		eval $labels
#
		[ "$TYPE" = "swap" ] && continue
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
	done < $target_dir/sys_disk_partitions.txt
	rmdir $srcdir
	#
	sudo sync
	echo "LIOS cloned into directory: $target_dir"
}
#
#  extract the python utility tweak_sfdisk.py
#
function tweak_sfdisk()
{
	cat > tweak_sfdisk.py <<"EOD"
#!/usr/bin/python3
#
import sys, os, os.path

argc = len(sys.argv)
sysdisk = ''
if argc > 1:
    sysdisk = sys.argv[1]
if len(sysdisk) == 0:
    print("Please specify a target disk.")
    sys.exit(1)
if not os.path.exists(sysdisk):
    print("Device does not exist: {}".format(sysdisk))
    sys.exit(1)
src_spec = ''
if argc > 2:
    src_spec = sys.argv[2]
if len(src_spec) == 0:
    print("Please specify a clone image directory.")
    sys.exit(1)
if not os.path.isdir(src_spec):
    print("Clone image directory: {} does not exist.".format(src_spec))
    sys.exit(1)
tar_spec = ''
if argc > 3:
    tar_spec = sys.argv[3]
if len(tar_spec) == 0:
    print("Please specify a sfdisk command file.")
    sys.exit(1)
try:
    sfout = open(tar_spec, "w")
except:
    print("Unable to open {} for writing.".format(tar_spec))
    sys.exit(7)

part = ''
if sysdisk[:9] == '/dev/nvme' or sysdisk[:8] == '/dev/mmc':
    part = 'p'

sysdisk_size = 0
bname = sysdisk.split('/')[-1]
try:
    with open('/sys/block/'+bname+'/size', 'rb') as fin:
        sysdisk_size = int(fin.read())
except:
    print("Unable to get disk size: {}".format(sysdisk))
    sys.exit(6)

print("Disk size: {}".format(sysdisk_size))

try:
    with open(src_spec + '/sys_disk_size.txt', 'rb') as fin:
        olast_lba = int(fin.read())
except:
    print("Unable to read disk size file")
    sys.exit(7)

nlast_lba = sysdisk_size
first_lba = 0
odisk = 'x'
olen = len(odisk)
with open(src_spec + '/sys_disk_sfdisk.dat', "r") as fin:
    for ln in fin:
        fields = ln.split()
        if len(fields) == 0:
            sfout.write('\n')
            continue

        if fields[0] == 'device:':
            odisk = fields[-1]
            olen = len(odisk)
            fields[-1] = sysdisk
        elif fields[0] == 'first-lba:':
            first_lba = int(fields[-1])
        elif fields[0] == 'last-lba:':
            olast_lba = int(fields[-1])
            nlast_lba = sysdisk_size - first_lba
            fields[-1] = str(nlast_lba)
        if fields[0][:olen] == odisk:
            pseq = fields[0][-1]
            fields[0] = sysdisk+part+pseq
            idx = 0
            size_idx = 0
            pstart = 0
            psize = 0
            for field in fields:
                if field == 'start=':
                    pstart = int(fields[idx+1][:-1])
                elif field == 'size=':
                    psize = int(fields[idx+1][:-1])
                    size_idx = idx + 1
                idx += 1
            if pstart + psize + 2048 > olast_lba:
                psize = nlast_lba - pstart
                fields[size_idx] = str(psize) + ','

        for field in fields:
            sfout.write(field)
            if field != fields[-1]:
                sfout.write(' ')
        sfout.write('\n')

sfout.close()
sys.exit(0)
EOD
	chmod +x tweak_sfdisk.py
}
#
function restore_to()
{
	local source target

	source=$1
	target=$2
	echo "Warning: All data on disk $target will be erased!"
	read -p "Continue?[Y]" confirm
	[ "x$confirm" != "xY" ] && return
	echo "Will restore from $source to $target"
	tweak_sfdisk
	./tweak_sfdisk.py $target $source /tmp/sys_disk_sfdisk.dat
	rm tweak_sfdisk.py
	sudo sfdisk $target < /tmp/sys_disk_sfdisk.dat
	sudo sync
#
	while read diskpart label_info
	do
		device=${diskpart%:*}
		eval $label_info
		case $TYPE in
		vfat)
			uuid=${UUID%-*}${UUID#*-}
			sudo mkfs -t $TYPE -n $LABEL -F 32 -i $uuid $device
			;;
		swap)
			sudo mkswap -L $LABEL -U $UUID $device
			;;
		xfs)
			sudo mkfs -t $TYPE -m uuid=$UUID -L $LABEL -f $device
			;;
		*)
			echo "Unknown file system type: $TYPE"
			continue
			;;
		esac
		[ "$TYPE" = "swap" ] && continue
#
		sudo mount -t $TYPE $device /mnt
		pushd /mnt
		echo "Restoring contents from $source/sys_disk_${LABEL}.cpio ..."
		sudo cpio -id < $source/sys_disk_${LABEL}.cpio
		popd
		sudo umount /mnt
	done < $source/sys_disk_partitions.txt
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
