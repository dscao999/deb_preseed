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
	ckey="GRUB_CMDLINE_LINUX_DEFAULT"
	con1="console=ttyS0,115200n8"
	con2="console=tty"
	sedscript="s/^${ckey}=.*$/${ckey}=\"${con1} ${con2}\"/"
	sed -i -e "${sedscript}" /etc/default/grub
	update-grub
fi
#
useradd -c "Default User, Automatic Login" -m ctos
passwd -d ctos
while [ ! -f /home/ctos/.bashrc ]
do
	sleep 1
done
sleep 1
cat >> /home/ctos/.bashrc <<"ENDDOC"
export LANG="zh_CN.UTF-8"
export LANGUAGE="zh_CN:zh"
#
#auto start X on startup
#
if [ x"$FROM_UPSTART" = x"yes" ]; then
	export FROM_UPSTART=
	TTY=${TTY:-$(tty)}
	TTY=${TTY#/dev/}

	if [[ $TTY != tty* ]]; then
		printf '==> ERROR: invalid TTY\n' >&2
		exit 1
	fi
	printf -v vt 'vt%02d' "${TTY#tty}"
	clear
	exec startx -- -keeptty $vt > /dev/null 2>&1
fi
ENDDOC
#
rm -f /etc/rc.local
mv /etc/rc.local.orig /etc/rc.local
sleep 5
reboot
