#!/bin/sh -e
#
client=$1
if [ "$client" != "citrix" -a "$client" != "vmware" -a \
	"$client" != "lidcc" -a "$client" != "firefox" ]
then
	echo "Unknown client: $client"
	exit 1
fi
if [ -z "$2" ]
then
	echo "No Web host specified."
	exit 2
fi
hostip=$2
host=http://$2/lenvdi/lenovo
#
TARGET=/target
[ -f $TARGET/etc/profile ] && sed -e '$aset -o vi' -i $TARGET/etc/profile
[ -f $TARGET/etc/skel/.bashrc ] && sed -e '$aset -o vi' -i $TARGET/etc/skel/.bashrc
[ -f $TARGET/home/lenovo/.bashrc ] && sed -e '$aset -o vi' -i $TARGET/home/lenovo/.bashrc
if [ -f $TARGET/etc/default/grub ]
then
	ckey1="GRUB_DISTRIBUTOR"
	cval1="LIOS V2"
	seds1="s/^${ckey1}=.*$/${ckey1}=\"${cval1}\"/"
	ckey2="GRUB_CMDLINE_LINUX_DEFAULT"
	cval2="quiet splash"
	seds2="s/^${ckey2}=.*$/${ckey2}=\"${cval2}\"/"
	sed -i -e "$seds1" -e "$seds2" $TARGET/etc/default/grub
	sed -i -e 's/^GRUB_TIMEOUT=.*$/GRUB_TIMEOUT=0/' $TARGET/etc/default/grub
fi
firmfile=i915-firmware.tar.xz
wget $host/$firmfile && unxz -c $firmfile | ( cd $TARGET/lib/firmware; tar -xf - )
#
mkdir $TARGET/var/log/journal
#
xfce_def=default-desktop.tar.xz
wget $host/$xfce_def && cp $xfce_def $TARGET/home/lenovo
xfce_empty=empty-desktop.tar.xz
wget $host/$xfce_empty && cp $xfce_empty $TARGET/home/lenovo
# VMware view installation bundle
vminst=VMware-Horizon-Client.x64.bundle
wget $host/$vminst && cp $vminst $TARGET/home/lenovo && \
	chmod +x $TARGET/home/lenovo/VMware-Horizon-Client.x64.bundle
icaclient=icaclient.tar.xz
wget $host/$icaclient && cp $icaclient $TARGET/home/lenovo
#
# copy ttyS0 login service, to fix baud at 115200
#
cp $TARGET/lib/systemd/system/serial-getty@.service \
	$TARGET/etc/systemd/system/serial-getty@ttyS0.service
sed -i -e 's/115200,38400,9600/115200/' $TARGET/etc/systemd/system/serial-getty@ttyS0.service
#
# Kill user processes after log out to avoid lingering processes, a bug of print applet
#
sed -i -e '/^#KillUserProcesses/aKillUserProcesses=yes' $TARGET/etc/systemd/logind.conf
#
# disable the loading of kvm
#
if [ -d $TARGET/etc/modprobe.d ]
then
	echo "blacklist irqbypass" >> $TARGET/etc/modprobe.d/local-blacklist.conf
	echo "install irqbypass /bin/false" >> $TARGET/etc/modprobe.d/local-blacklist.conf
	echo "blacklist kvm" >> $TARGET/etc/modprobe.d/local-blacklist.conf
	echo "install kvm /bin/false" >> $TARGET/etc/modprobe.d/local-blacklist.conf
	echo "blacklist kvm_intel" >> $TARGET/etc/modprobe.d/local-blacklist.conf
	echo "install kvm_intel /bin/false" >> $TARGET/etc/modprobe.d/local-blacklist.conf
fi
#
# change apt sources.list
#
debline="deb [allow-insecure=yes arch=amd64,all] http://$hostip/lenvdi lenvdi main"
sed -i -e "\$a${debline}" $TARGET/etc/apt/sources.list
#
# set EFI ESP label to LIOS_ESP
#
efidev=$(mount|fgrep "$TARGET/boot/efi" |cut -d' ' -f1)
if [ -n "$efidev" ]
then
	sync && fatlabel $efidev LIOS_ESP && sync
fi
#
endline=93
#
[ -f $TARGET/etc/rc.local ] && mv $TARGET/etc/rc.local $TARGET/etc/rc.local.orig
#
tail -n +${endline} $0 | sed -e "s/^vmhorizon=.*/vmhorizon=$client/" \
		-e "s/cn.pool.ntp.org/$hostip/" > $TARGET/etc/rc.local
chmod +x $TARGET/etc/rc.local
exit 0
#END OF SCRIPT
#!/bin/bash -e
#
# one time task after installation
#
install_vmhorizon ()
{
	bundle=$1
	if [ ! -x $bundle ]
	then
		echo "Cannot execute $bundle"
		return 1
	fi
	export TERM=dumb
	export VMWARE_EULAS_AGREED=yes
	$bundle --console --required
}
#
purge_libreoffice ()
{
	apt-get update
	apt-get -y --allow-unauthenticated install lios-greeter-themes lenvdi-tools
	case "$vmhorizon" in
		"lidcc")
			apt-get -y --allow-unauthenticated install lidc-client
			;;
		"vmware")
			install_vmhorizon $vminstf
			;;
		"citrix")
			apt-get -y --allow-unauthenticated install ctxusb
			;;
		"firefox")
			;;
		*)
			echo "unknown vmhorizon value: $vmhorizon"
			exit 1
	esac
#
	apt-get -y purge libreoffice-core libreoffice-common mythes-en-us uno-libs3 ure
	apt-get -y autoremove
	apt-get -y dist-upgrade
	rcpkgs=$(dpkg --list | grep -E '^rc ' |  awk '{print $2}')
	[ -n "$rcpkgs" ] && dpkg --purge $rcpkgs
	echo "Purge Complete!, vmhorizon: $vmhorizon"
}
#
vmhorizon=lidcc
#
exec 1> /home/lenovo/rc-local.log 2>&1
#set -x
#
xfce_def=/home/lenovo/default-desktop.tar.xz
xfce_empty=/home/lenovo/empty-desktop.tar.xz
icaclient=/home/lenovo/icaclient.tar.xz
vminstf=/home/lenovo/VMware-Horizon-Client.x64.bundle
#
purge_libreoffice &
#
auto_user=liosuser
mkdir /etc/lightdm/lightdm.conf.d
cat <<EOD > /etc/lightdm/lightdm.conf.d/01autologin.conf
[Seat:*]
autologin-user=$auto_user
autologin-user-timeout=0
EOD
#
su -c "unxz -c $xfce_def | tar -xf -" - lenovo
cat > /home/lenovo/.vimrc <<"ENDDOC"
filetype plugin indent on
syntax on
set title
set tabstop=8
set softtabstop=8
set shiftwidth=8
set noexpandtab
set mouse=
ENDDOC
chown lenovo:lenovo /home/lenovo/.vimrc
#
useradd -c "Default User, Automatic Login" -m -s /bin/bash $auto_user
#
while [ ! -d /home/$auto_user ]
do
	sleep 1
done
#
cat > /home/$auto_user/.i18n <<"ENDDOC"
LANG=zh_CN.utf8
ENDDOC
#
cat >> /home/$auto_user/.xsessionrc <<"ENDDOC"
##
## set variable LANG from .i18n, automatically generated
## do not edit
##
if [ -r $PWD/.i18n ]
then
	. ${PWD}/.i18n
fi
ENDDOC
#
chown ${auto_user}:${auto_user} /home/$auto_user/.xsessionrc
#
su -c "unxz -c $xfce_empty | tar -xf -" - $auto_user
su -c "unxz -c $icaclient /home/lenovo/icaclient.tar.xz | tar -xf -" - $auto_user
#
[ -d /etc/xdg/xfce4/kiosk ] || mkdir /etc/xdg/xfce4/kiosk
echo "[xfce4-session]" > /etc/xdg/xfce4/kiosk/kioskrc
echo "SaveSession=lenovo" >> /etc/xdg/xfce4/kiosk/kioskrc
#
panel=xfce4/xfconf/xfce-perchannel-xml
if [ -d /etc/xdg/$panel ]
then
	sed -e "/^<channel name=/s/>/ locked=\"$auto_user\">/" \
		/home/$auto_user/.config/$panel/xfce4-panel.xml > /etc/xdg/$panel/xfce4-panel.xml
fi
#
ntp_server=cn.pool.ntp.org
if [ -n "$ntp_server" ]
then
	sed -i -e "s/^#NTP=$/NTP=${ntp_server}/" /etc/systemd/timesyncd.conf
fi
#
if /bin/echo 123 > /dev/ttyS0
then
	systemctl enable serial-getty@ttyS0.service
fi
#
appdesk=/usr/share/applications
defdesk=xfce4/panel/launcher-19/16221051582.desktop
usrdesk=xfce4/panel/launcher-10/16209940802.desktop
swapdev=$(swapon -s | fgrep /dev | awk '{print $1}')
if [ -b $swapdev ]
then
	eval $(blkid $swapdev|cut -d: -f2)
	set_uuid=
	[ -n "$UUID" ] && set_uuid="--uuid $UUID"
	swapoff $swapdev
	mkswap -f --label LIOS_SWAP $set_uuid $swapdev
fi
#
# modify /etc/fstab so that /boot and /boot/efi are mounted readonly
#
sed -i -e '/boot[ \t]/s/defaults/ro,&/' -e '/boot\/efi/s/umask=0077/ro,&/' /etc/fstab
#
wait
if dpkg --list icaclient
then
	autoapp=$appdesk/selfservice.desktop
	if systemctl --all list-units | fgrep ctxlogd > /dev/null 2>&1
	then
		systemctl enable ctxlogd
	fi
	icaroot=/opt/Citrix/ICAClient
	[ -w ${icaroot}/config/module.ini ] && \
	sed -i -e '/^\[WFClient/aDesktopApplianceMode=TRUE' ${icaroot}/config/module.ini
	[ -r $autoapp ] && cp $autoapp /home/$auto_user/.config/autostart/
#
elif [ -r $appdesk/vmware-view.desktop ]
then
	cp $appdesk/vmware-view.desktop /home/$auto_user/.config/autostart/
	cp $appdesk/vmware-view.desktop /home/$auto_user/.config/$usrdesk
	cp $appdesk/vmware-view.desktop /home/lenovo/.config/$defdesk
#
elif dpkg --list lidc-client
then
	if [ -r $appdesk/lidc-client.desktop ]
	then
		cp $appdesk/lidc-client.desktop /home/$auto_user/.config/autostart/
		cp $appdesk/lidc-client.desktop /home/$auto_user/.config/$usrdesk
		cp $appdesk/lidc-client.desktop /home/lenovo/.config/$defdesk
	fi
elif [ -f $appdesk/seturl.desktop ]
then
	firstshot=.config/autostart/first-shot.desktop
	eval su - $auto_user -c \'"cp $appdesk/seturl.desktop $firstshot"\'
fi
#
rm -f $vminstf $icaclient $xfce_empty $xfce_def
#
plymouth-set-default-theme -R lenvdi
update-grub2
#
mv /etc/rc.local /etc/rc.local.once
[ -f /etc/rc.local.orig ] && mv /etc/rc.local.orig /etc/rc.local
sync
target=$(systemctl get-default)
while ! loginctl --no-legend list-sessions | fgrep lightdm
do
	sleep 1
done
systemctl reboot
