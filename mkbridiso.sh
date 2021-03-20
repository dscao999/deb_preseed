#!/bin/bash
#
LABEL=LENOVO_LIOS_V2_AMD64
EFIIMAGE=boot/grub/efi.img

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
	xorriso -as mkisofs -r -V $LABEL \
		-o $OUTISO \
		-isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
		-b isolinux/isolinux.bin -c isolinux/boot.cat -boot-load-size 4 \
		-boot-info-table -no-emul-boot  -eltorito-alt-boot \
		-e $EFIIMAGE -no-emul-boot -isohybrid-gpt-basdat \
		$ISODIR
}

isotop=$1
oiso=$2
[ -z "$isotop" ] && isotop=isotop
[ -n "$3" ] && LABEL="$3"
[ -n "$4" ] && EFIIMAGE="$4"
mkiso $isotop hybrid.iso
