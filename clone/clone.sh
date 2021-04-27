#target_dir=/var/www/html/debian/clone-$$
target_dir=/var/www/html/debian/clone
[ -d $target_dir ] && rm -rf $target_dir
mkdir $target_dir
#
parts=$(sudo blkid | fgrep LIOS | awk -F": " '{print $1}')
if [ ${#parts} -eq 0 ]
then
	echo "No system to clone. Not a LIOS system?"
	exit 1
fi
#
for part in ${parts[@]}
do
	echo "Partition with file system: $part"
done
#
sysdisk=${parts[0]%%[0-9]*}
echo "SYS Disk is: $sysdisk"
touch $target_dir/sys_disk_sfdisk.dat
sudo sfdisk --dump ${sysdisk} > $target_dir/sys_disk_sfdisk.dat
pstart=$(fgrep ${sysdisk}1 $target_dir/sys_disk_sfdisk.dat|awk '{print $4}')
pstart=${pstart%,}
echo "Partition Start Sector: ${pstart}"
touch $target_dir/grub_code.dat
sudo dd if=${sysdisk} of=$target_dir/grub_code.dat bs=512 count=$pstart
#
#  mount and copy file system
#
srcdir=${PWD}/src-$$
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
}
#
trap cleanup EXIT INT
#
[ -d $srcdir ] || mkdir $srcdir
for dpart in ${parts[@]}
do
	eval pidx=${dpart#${sysdisk}}
	sudo mount -o ro $dpart $srcdir
	touch $target_dir/sys_disk_p${pidx}.cpio
	tsize=$(df -k | fgrep $dpart | awk '{print $3}')
	[ $tsize -gt 1232896 ] && \
	echo "Copying files in $dpart, $tsize KBytes, Please wait for a while..."
	pushd $srcdir
	sudo find . -print | sudo cpio -o > $target_dir/sys_disk_p${pidx}.cpio
	popd
	sudo umount $dpart
done
cleanup
exit 0
