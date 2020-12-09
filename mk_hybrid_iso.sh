#!/bin/bash
#
function mkiso()
{
	ISODIR=$1
	OUTISO=$2

	[ -z "$ISODIR" ] && ISODIR=isotop
	if [ ! -d "$ISODIR" ]
	then
		echo "Invalid ISO Top Directory: $ISODIR"
		exit 1
	fi
	[ -z "$OUTISO" ] && OUTISO=hybrid.iso
	[ -f "$OUTISO" ] && rm $OUTISO
	#
	chmod u+w ${ISODIR}/isolinux/isolinux.bin
	cp /usr/lib/ISOLINUX/isolinux.bin $ISODIR/isolinux/isolinux.bin
	xorriso -as mkisofs -r -V 'LENOVO_LIOS_V2_AMD64' \
		-o $OUTISO \
		-isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
		-b isolinux/isolinux.bin -c isolinux/boot.cat -boot-load-size 4 \
		-boot-info-table -no-emul-boot  -eltorito-alt-boot \
		-e boot/grub/efi.img -no-emul-boot -isohybrid-gpt-basdat \
		$ISODIR
}

srciso=./srciso-$$.iso
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

trap exit_trap INT

mirror=
splash=
rootdisk=
TARGS=$(getopt -l mirror:,splash:,rootdisk: -o m:s:r: -- "$@")
[ $? -eq 0 ] || exit 1
eval set -- $TARGS
while true
do
	case "$1" in
		--rootdisk)
			rootdisk=$2
			shift
			;;
		--mirror)
			mirror=$2
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

isofile=$1
wdir=${PWD}
[ "${rootdisk}" = "/dev/sda" ] && rootdisk=
[ "${mirror}" = "ftp2.cn.debian.org" ] && mirror=
[ -n "${rootdisk}" ] && srootdisk="s| /dev/sda$| ${rootdisk}|"
[ -n "${mirror}" ] && shttphost="s| ftp2\\.cn\\.debian\\.org$| ${mirror}|"

fln=109
tail -n +${fln} $0 > ${srciso}
sudo mount -o ro ${srciso} ${srcdir}
pushd ${srcdir}
find . -print | cpio -pd ${wdir}/${dstdir} > /dev/null
popd
if [ -n "$splash" -a -f "$splash" ]
then
	cp $splash ${dstdir}/isolinux/splash.png
fi
if [ -n "$srootdisk" -o -n "$shttphost" ]
then
	sed -i -e "$srootdisk" -e "$shttphost" ${dstdir}/preseed-debian.cfg
fi

mkiso ${dstdir} ${isofile}
cleanup
exit 0
#END OF SCRIPT
