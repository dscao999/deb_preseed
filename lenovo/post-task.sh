#!/bin/sh -e
#
TARGET=/target
[ -f $TARGET/etc/profile ] && sed -e '$aset -o vi' -i $TARGET/etc/profile
[ -f $TARGET/etc/skel/.bashrc ] && sed -e '$aset -o vi' -i $TARGET/etc/skel/.bashrc
[ -f $TARGET/home/lenovo/.bashrc ] && sed -e '$aset -o vi' -i $TARGET/home/lenovo/.bashrc
if [ -f $TARGET/etc/default/grub ]
then
	ckey="GRUB_CMDLINE_LINUX_DEFAULT"
	cval="console=ttyS0,115200n8 splash"
	seds1="s/^${ckey}=.*$/${ckey}=\"${cval}\"/"
	sed -i -e "$seds1" $TARGET/etc/default/grub
fi
firmfile=/cdrom/lenovo/i915-firmware.tar.xz
if [ -f $firmfile ]
then
	unxz -c $firmfile | ( cd $TARGET/lib/firmware; tar -xf - )
fi
mkdir $TARGET/var/log/journal
#
xfce_def=/cdrom/lenovo/default-desktop.tar.xz
xfce_empty=/cdrom/lenovo/empty-desktop.tar.xz
if [ -f $xfce_def -a -d $TARGET/home/lenovo ]
then
	[ -f $xfce_empty ] && cp $xfce_empty $TARGET/home/lenovo
	cp $xfce_def $TARGET/home/lenovo
fi
#
# Kill user processes after log out to avoid lingering processes, a bug of print applet
#
sed -i -e '/^#KillUserProcesses/aKillUserProcesses=yes' $TARGET/etc/systemd/logind.conf
#
endline=41
#
[ -f $TARGET/etc/rc.local ] && mv $TARGET/etc/rc.local $TARGET/etc/rc.local.orig
#
tail -n +${endline} $0 > $TARGET/etc/rc.local
chmod +x $TARGET/etc/rc.local
exit 0
#END OF SCRIPT
#!/bin/bash -e
#
# one time task after installation
#
exec 1> /home/lenovo/rc-local.log 2>&1
#
update-grub2
auto_user=liosuser
mkdir /etc/lightdm/lightdm.conf.d
cat <<EOD > /etc/lightdm/lightdm.conf.d/01autologin.conf
[Seat:*]
autologin-user=$auto_user
autologin-user-timeout=0
EOD
#
su -c "unxz -c /home/lenovo/default-desktop.tar.xz | tar -xf -" - lenovo
#
useradd -c "Default User, Automatic Login" -m -s /usr/bin/bash $auto_user
#
while [ ! -d /home/$auto_user ]
do
	sleep 1
done
#
cat >> /home/$auto_user/.xsessionrc <<"ENDDOC"
export LANG="zh_CN.UTF-8"
export LANGUAGE="zh_CN:zh"
##
##auto start lios proxy on startup
##
ENDDOC
#
chown ${auto_user}:${auto_user} /home/$auto_user/.xsessionrc
#
su -c "unxz -c /home/lenovo/empty-desktop.tar.xz | tar -xf -" - $auto_user
#
mv /etc/rc.local /etc/rc.local.once
[ -f /etc/rc.local.orig ] && mv /etc/rc.local.orig /etc/rc.local
sync
target=$(systemctl get-default)
while ! loginctl --no-legend list-sessons | fgrep lightdm
do
	sleep 1
done
systemctl reboot
