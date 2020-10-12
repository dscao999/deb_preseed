ISODIR=isotop
cp /usr/lib/ISOLINUX/isolinux.bin $ISODIR/isolinux/isolinux.bin
xorriso -as mkisofs -r -V 'LENOVO_LIOS_V1_AMD64' \
	-o hybrid_dvd.iso \
	-isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
	-b isolinux/isolinux.bin -c isolinux/boot.cat -boot-load-size 4 \
	-boot-info-table -no-emul-boot  -eltorito-alt-boot \
	-e boot/grub/efi.img -no-emul-boot -isohybrid-gpt-basdat \
	$ISODIR
