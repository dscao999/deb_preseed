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
# add auto-login for ctos
#
cat >> /etc/init/autologin-ctos.conf <<"ENDDOC1"
#
# Autologin - Automatically login as ctos on tty7
#
# based on nodm

description	"X starter"
author		"Wang Shishuang <wangss@cloud-times.com>"

start on ((filesystem and stopped rc
           and runlevel [!06]
           and started dbus
           and (drm-device-added card0 PRIMARY_DEVICE_FOR_DISPLAY=1
                or stopped udev-fallback-graphics))
          or runlevel PREVLEVEL=S)

stop on runlevel [016]

respawn

emits login-session-start
emits desktop-session-start
emits desktop-shutdown

script
    if [ -n "$UPSTART_EVENTS" ]
    then
        # Check kernel command-line for inhibitors, unless we are being called
        # manually
        for ARG in $(cat /proc/cmdline); do
            if [ "$ARG" = "text" ]; then
		plymouth quit || : 
                stop
		exit 0
            fi
        done

	if [ "$RUNLEVEL" = S -o "$RUNLEVEL" = 1 ]
	then
	    # Single-user mode
	    plymouth quit || :
	    exit 0
	fi
    fi

    exec /sbin/getty -8 38400 -o "-f \u FROM_UPSTART=yes" -a ctos tty7
end script

post-stop script
	if [ "$UPSTART_STOP_EVENTS" = runlevel ]; then
		initctl emit desktop-shutdown
	fi
end script
ENDDOC1
#
rm -f /etc/rc.local
mv /etc/rc.local.orig /etc/rc.local
sleep 5
reboot
