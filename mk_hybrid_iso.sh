#!/bin/bash
#
if ! sudo ls /tmp > /dev/null 2>&1
then
        echo "Require sudo priviledge"
        exit 1
fi
#
eval OSNAME=$(sed -e '/^NAME=/!d' /etc/os-release | cut -d= -f2)
case $OSNAME in
	"Debian GNU/Linux")
#
# default values for Debian
#
		ISOLABEL="LENOVO_LIOS_V2_AMD64"
		ISOLXBIN=/usr/lib/ISOLINUX/isolinux.bin
		EFIIMAGE=boot/grub/efi.img
		HDPFXBIN=/usr/lib/ISOLINUX/isohdpfx.bin
		;;
	"Fedora")
#
# default values for Fedora
#
                ISOLABEL="LENOVO_LIOS_V2_AMD64"
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
	cp ${ISOLXBIN} $ISODIR/isolinux/isolinux.bin
	xorriso -as mkisofs -r -V ${ISOLABEL} \
		-o $OUTISO \
		-isohybrid-mbr ${HDPFXBIN} \
		-b isolinux/isolinux.bin -c isolinux/boot.cat -boot-load-size 4 \
		-boot-info-table -no-emul-boot  -eltorito-alt-boot \
		-e ${EFIIMAGE} -no-emul-boot -isohybrid-gpt-basdat \
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

pass=P@ssw0rd
nontp=no
mirror=
splash=
rootdisk=
TARGS=$(getopt -l mirror:,splash:,rootdisk:,ntp:,nontp,pass: -o m:s:r:t:np: -- "$@")
[ $? -eq 0 ] || exit 1
eval set -- $TARGS
while true
do
	case "$1" in
		--pass)
			pass="$2"
			shift
			;;
		--nontp)
			nontp=yes
			;;
		--ntp)
			ntpsvr=$2
			shift
			;;
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

passed=
if [ "$pass" != "P@ssw0rd" ]
then
	salt="$(date +%D%H%M%S)"
	passed="$(mkpasswd $pass $salt -m sha-256)"
fi

isofile=$1
wdir=${PWD}
[ "${rootdisk}" = "/dev/sda" ] && rootdisk=
[ "${mirror}" = "mirrors.ustc.edu.cn" ] && mirror=
[ -n "${rootdisk}" ] && srootdisk="s# /dev/sda\$# ${rootdisk}#"
[ -n "${mirror}" ] && shttphost="s#mirrors\\.ustc\\.edu\\.cn\$#${mirror}#"
[ -n "${ntpsvr}" ] && sntpsvr="s#cn\\.pool\\.ntp\\.org\$#${ntpsvr}#"
[ "${nontp}" = "yes" ] && snontp="/^d-i  *clock-setup\\/ntp  *boolean  *true\$/s/true\$/false/"
[ -n "${passed}" ] && spassed="s;\(user-password-crypted password \).*$;\1$passed;"

fln=174
tail -n +${fln} $0 > ${srciso}
sudo mount -o ro ${srciso} ${srcdir}
pushd ${srcdir}
find . -print | cpio -pd ${wdir}/${dstdir} > /dev/null
popd
if [ -n "$splash" -a -f "$splash" ]
then
	cp $splash ${dstdir}/isolinux/splash.png
fi
[ -n "${srootdisk}" ] && sed -i -e "$srootdisk" ${dstdir}/preseed-debian.cfg
[ -n "${shttphost}" ] && sed -i -e "$shttphost" ${dstdir}/preseed-debian.cfg
[ -n "${snontp}" ] && sed -i -e "$snontp" ${dstdir}/preseed-debian.cfg
chmod u+w ${dstdir}/lenovo ${dstdir}/lenovo/post-task.sh
if [ -n "${sntpsvr}" ]
then
	sed -i -e "$sntpsvr" ${dstdir}/preseed-debian.cfg
	sed -i -e "s/^ntp_server=.*$/ntp_server=${ntpsvr}/" ${dstdir}/lenovo/post-task.sh
fi
if [ -n "${snontp}" ]
then
	sed -i -e "s/^ntp_server=.*$/ntp_server=/" ${dstdir}/lenovo/post-task.sh
fi
[ -n "${spassed}" ] && sed -i -e "$spassed" ${dstdir}/preseed-debian.cfg
#
mkiso ${dstdir} ${isofile}
cleanup
exit 0
#END OF SCRIPT
