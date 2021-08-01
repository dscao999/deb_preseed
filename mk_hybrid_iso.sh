#!/bin/bash
#
if ! sudo ls /etc > /dev/null 2>&1
then
	echo "sudo failed. sudo privilege  is required for this operation."
	exit 1
fi
#
eval OSNAME=$(sed -e '/^NAME=/!d' /etc/os-release | cut -d= -f2)
case $OSNAME in
	"Debian GNU/Linux")
#
# default values for Debian
#
		ISOLXBIN=/usr/lib/ISOLINUX/isolinux.bin
		EFIIMAGE=boot/grub/efi.img
		HDPFXBIN=/usr/lib/ISOLINUX/isohdpfx.bin
		;;
	"Fedora")
#
# default values for Fedora
#
                ISOLXBIN=/usr/share/syslinux/isolinux.bin
                EFIIMAGE=boot/grub/efi.img
                HDPFXBIN=/usr/share/syslinux/isohdpfx.bin
		;;
	*)
		echo "Unsupported OS type"
		exit 1
		;;
esac
#
function mkiso()
{
	local ISODIR OUTISO

	ISODIR=$1
	OUTISO=$2
	[ -z "$ISODIR" ] && ISODIR=isotop
	if [ ! -d "$ISODIR" ]
	then
		echo "Invalid ISO Top Directory: $ISODIR"
		exit 1
	fi
	[ -z "$OUTISO" ] && OUTISO=-
	[ -f "$OUTISO" ] && rm $OUTISO
	#
	chmod u+w ${ISODIR}/isolinux/isolinux.bin
	cp ${ISOLXBIN} $ISODIR/isolinux/isolinux.bin
	xorriso -as mkisofs -r -volid "${ISOLABEL}" \
		-o $OUTISO \
		-isohybrid-mbr ${HDPFXBIN} \
		-b isolinux/isolinux.bin -c isolinux/boot.cat -boot-load-size 4 \
		-boot-info-table -no-emul-boot  -eltorito-alt-boot \
		-e ${EFIIMAGE} -no-emul-boot -isohybrid-gpt-basdat \
		$ISODIR
}

srciso=srciso-$$.iso
srcdir=srcdir-$$
dstdir=dstdir-$$
rm -rf $srcdir
mkdir $srcdir
rm -rf $dstdir
mkdir $dstdir

function cleanup()
{
	if mountpoint -q ${srcdir}
	then
		sudo umount ${srcdir}
	fi
	rm -f ${srciso}
	sudo rm -rf ${srcdir} ${dstdir}
}

function exit_trap()
{
	cleanup
	exit 1
}

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

trap exit_trap INT EXIT

pass=P@ssw0rd
nontp=no
mirror=
splash=
themes=
myclient=lidcc
TARGS=$(getopt -l splash:,pass:,client: \
	-o s:p:c: -- "$@")
[ $? -eq 0 ] || exit 1
eval set -- $TARGS
while true
do
	case "$1" in
		--client)
			myclient="$2"
			shift
			;;
		--pass)
			pass="$2"
			shift
			;;
		--splash)
			splash=$2
			shift
			;;
		--)
			shift
			break
			;;
	esac
	shift
done

passed=
if [ "$pass" != "P@ssw0rd" ]
then
	salt="$(date +%D%H%M%S)"
	passed="$(mkpasswd $pass $salt -m sha-256)"
fi

isofile=$1
[ -z "$isofile" ] && isofile=hybrid.iso
if [ "${isofile#/dev/}" = "$isofile" ]
then
	TOUSB=0
else
	check_usbdisk $isofile
	TOUSB=1
fi
#
wdir=${PWD}
[ -n "${passed}" ] && spassed="s;\(user-password-crypted password \).*$;\1$passed;"
#
fln=234
tail -n +${fln} $0 > ${srciso}
sudo mount -o ro ${srciso} ${srcdir}
loopdev=$(sudo losetup|fgrep ${srciso})
eval $(sudo blkid $loopdev|cut -d: -f2)
ISOLABEL=$LABEL
#
pushd ${srcdir}
find . -print | cpio -pd ${wdir}/${dstdir} > /dev/null
popd
#
PRESEED=${dstdir}/preseed-debian.cfg
chmod u+w $PRESEED
[ -n "${spassed}" ] && sed -i -e "$spassed" $PRESEED
case "${myclient}" in
	"vmware")
		;;
	"citrix")
		;;
	"lidcc")
		;;
	"firefox")
		;;
	*)
		echo "Selected client is not valid: ${myclient}"
		exit 1
esac
sed -i -e "s/post-task-net.sh [a-z][a-z]* /post-task-net.sh ${myclient} /" $PRESEED
#
#  adapt ip in preseed.cfg to current IP
#
hit=0
while [ $hit -eq 0 ]
do
	for nic in $(ls /sys/class/net)
	do
		type=$(cat /sys/class/net/$nic/type)
		if [ $type -eq 1 ]
		then
			ipaddr=$(ip addr show dev $nic|fgrep "inet "|awk '{print $2}')
			if [ -n "$ipaddr" ]
			then
				hit=1
				break;
			fi
		fi
	done
	sleep 3
done
if [ $hit -eq 0 ]
then
	echo "No NIC has an IP address."
	exit 1
fi
ipaddr=${ipaddr%/*}
sed -i -e "s#[1-9][0-9]*\.[1-9][0-9]*\.[1-9][0-9]*\.[1-9][0-9]*#$ipaddr#" $PRESEED
#
if [ $TOUSB -eq 1 ]
then
	mkiso ${dstdir} | sudo dd of=${isofile} obs=128K oflag=direct conv=nocreat
else
	mkiso ${dstdir} ${isofile}
fi
#cleanup
exit 0
#END OF SCRIPT
