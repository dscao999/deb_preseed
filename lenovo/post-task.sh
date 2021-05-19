#!/bin/sh -e
#
client=$1
if [ "$client" != "citrix" -a "$client" != "vmware" -a \
	"$client" != "lidcc" ]
then
	echo "Unknown client: $client"
	exit 1
fi
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
firmfile=/cdrom/lenovo/i915-firmware.tar.xz
if [ -f $firmfile ]
then
	unxz -c $firmfile | ( cd $TARGET/lib/firmware; tar -xf - )
fi
mkdir $TARGET/var/log/journal
#
xfce_def=/cdrom/lenovo/default-desktop.tar.xz
xfce_empty=/cdrom/lenovo/empty-desktop.tar.xz
icaclient=/cdrom/lenovo/icaclient.tar.xz
rootca=/cdrom/lenovo/rootca.pem
if [ -f $xfce_def -a -d $TARGET/home/lenovo ]
then
	[ -f $xfce_empty ] && cp $xfce_empty $TARGET/home/lenovo
	cp $xfce_def $TARGET/home/lenovo
	[ -f $icaclient ] && cp $icaclient $TARGET/home/lenovo
fi
# VMware view installation bundle
vminst=/cdrom/pool/lenvdi/VMware-Horizon-Client.x64.bundle
[ -f $vminst ] && cp $vminst $TARGET/home/lenovo && \
	chmod +x $TARGET/home/lenovo/VMware-Horizon-Client.x64.bundle
[ -f $rootca ] && cp $rootca $TARGET/home/lenovo
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
# set EFI ESP label to LIOS_ESP
#
efidev=$(mount|fgrep "$TARGET/boot/efi" |cut -d' ' -f1)
if [ -n "$efidev" ]
then
	sync && fatlabel $efidev LIOS_ESP && sync
fi
#
endline=87
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
purge_libreoffice ()
{
	apt-get -y purge libreoffice-core libreoffice-common mythes-en-us uno-libs3 ure
	apt-get -y autoremove
	apt-get -y dist-upgrade
	rcpkgs=$(dpkg --list | grep -E '^rc ' |  awk '{print $2}')
	[ -n "$rcpkgs" ] && dpkg --purge $rcpkgs
	if [ $vmhorizon -eq 1 ] || dpkg --list icaclient > /dev/null 2>&1
	then
		if dpkg --list lidc-client
		then
			apt-get -y purge lidc-client virt-viewer
			apt-get -y autoremove
		fi
	fi
}

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
vmhorizon=0
#
exec 1> /home/lenovo/rc-local.log 2>&1
#
purge_libreoffice &
#
xfce_def=/home/lenovo/default-desktop.tar.xz
xfce_empty=/home/lenovo/empty-desktop.tar.xz
icaclient=/home/lenovo/icaclient.tar.xz
vminstf=/home/lenovo/VMware-Horizon-Client.x64.bundle
if [ $vmhorizon -eq 1 ]
then
	install_vmhorizon $vminstf
fi
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
rm -f $vminstf $icaclient $xfce_empty $xfce_def
#
appdesk=/usr/share/applications
usrdesk=xfce4/panel/launcher-10/16209940802.desktop
if dpkg --list icaclient > /dev/null 2>&1
then
	autoapp=$appdesk/selfservice.desktop
	if systemctl --all list-units | fgrep ctxlogd > /dev/null 2>&1
	then
		systemctl enable ctxlogd
	fi
	icaroot=/opt/Citrix/ICAClient
	[ -w ${icaroot}/config/module.ini ] && \
	sed -i -e '/^\[WFClient/aDesktopApplianceMode=TRUE' ${icaroot}/config/module.ini
	if [ -f /home/lenovo/rootca.pem ]
	then
		cp /home/lenovo/rootca.pem ${icaroot}/keystore/cacerts/
		${icaroot}/util/ctx_rehash
		rm -f /home/lenovo/rootca.pem
	fi
	[ -r $autoapp ] && cp $autoapp /home/$auto_user/.config/autostart/
#
elif [ -r $appdesk/vmware-view.desktop ]
then
	cp $appdesk/vmware-view.desktop /home/$auto_user/.config/autostart/
#
elif dpkg --list lidc-client > /dev/null 2>&1
then
	if [ -f /home/lenovo/rootca.pem ]
	then
		cp /home/lenovo/rootca.pem /etc/ssl/certs/oVirt-rootca.pem
		pushd /etc/ssl/certs
		index=$(openssl x509 -noout -hash -in oVirt-rootca.pem)
		ln -s oVirt-rootca.pem ${index}.0
		popd
	fi
	if [ -r $appdesk/lidc-client.desktop ]
	then
		cp $appdesk/lidc-client.desktop /home/$auto_user/.config/autostart/
		cp $appdesk/lidc-client.desktop /home/$auto_user/.config/$usrdesk
	fi
fi
#
swapdev=$(swapon -s | fgrep /dev | awk '{print $1}')
if [ -b $swapdev ]
then
	info_line="$(blkid $swapdev)"
	for vari in $info_line
	do
		[ ${vari%=*} = ${vari} ] && continue
		eval $vari
	done
	swapoff $swapdev
	mkswap --label LIOS_SWAP --uuid $UUID $swapdev
fi
wait
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
