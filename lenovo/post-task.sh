#!/bin/sh -e
#
TARGET=/target
sed -e '$aset -o vi' -i $TARGET/etc/profile
if [ ! -d $TARGET/init ] 
then
	echo "$TARGET/init does not exit"
else
	echo "$TARGET/init exists"
fi
if [ ! -f $TARGET/etc/rc.local ]
then
	echo "$TARGET/etc/rc.local does not exit"
	exit 0
else
	echo "$TARGET/etc/rc.local exits"
fi
#
endline=27
#
mv $TARGET/etc/rc.local $TARGET/etc/rc.local.orig
#
tail -n +${endline} $0 > $TARGET/etc/rc.local
chmod +x $TARGET/etc/rc.local
exit 0
END OF SCRIPT
#!/bin/bash -e
#
# one time task after installation
#
if [ -f /etc/init/tty1.conf ]
then
	cp /etc/init/tty1.conf /etc/init/ttyS0.conf
	sed -i -e 's/tty1/ttyS0/g' -e 's/38400/115200/' /etc/init/ttyS0.conf
fi
if [ -f /etc/default/grub ]
then
	sed -i -e 's/GRUB_CMDLINE_LINUX_DEFAULT=.*$/GRUB_CMDLINE_LINUX_DEFAULT=/' /etc/default/grub
	update-grub
fi
#
useradd -c "Default User, Automatic Login" -m ctos
passwd -d ctos
#
rm -f /etc/rc.local
mv /etc/rc.local.orig /etc/rc.local
#
exit 0
