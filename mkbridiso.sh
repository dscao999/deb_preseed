#!/bin/bash
#
TARGS=$(getopt -l label:,output:,efi: -o l:o: -- "$@")
[ $? -ne 0 ] && exit 1
#
LABEL=LENOVO_LIOS_V2_AMD64
EFIIMAGE=boot/grub/efi.img
#
eval set -- $TARGS
while true; do
	case "$1" in
	"--efi")
		EFIIMAGE=$2
		shift
		;;
	"--label")
		LABEL=$2
		shift
		;;
	"-l")
		LABEL=$2
		shift
		;;
	"--output")
		OUTISO=$2
		shift
		;;
	"-o")
		OUTISO=$2
		shift
		;;
	"--")
		shift
		break
		;;
	esac
	shift
done
#
ISODIR=$1
#
function mkiso()
{
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
	cp /usr/lib/ISOLINUX/isolinux.bin $ISODIR/isolinux/isolinux.bin
	xorriso -as mkisofs -r -volid "$LABEL" \
		-o $OUTISO \
		-isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
		-b isolinux/isolinux.bin -c isolinux/boot.cat -boot-load-size 4 \
		-boot-info-table -no-emul-boot  -eltorito-alt-boot \
		-e $EFIIMAGE -no-emul-boot -isohybrid-gpt-basdat \
		$ISODIR
}

mkiso
