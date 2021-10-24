#!/bin/sh -e
#
client=$1
if [ "$client" != "citrix" -a "$client" != "vmware" -a \
	"$client" != "lidcc" -a "$client" != "firefox" \
	-a "$client" != "lidcc-edu" ]
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
cdrom=/cdrom/lenovo
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
# VMware view installation bundle
vminst=VMware-Horizon-Client.x64.bundle
firmfile=i915-firmware.tar.xz
xfce_def=default-desktop.tar.xz
xfce_empty=empty-desktop.tar.xz
icaclient=icaclient.tar.xz
bigagent=lidmagent.tar.gz
if [ -f $cdrom/$firmfile ]
then
	unxz -c $cdrom/$firmfile | ( cd $TARGET/lib/firmware; tar -xf - )
	cp $cdrom/$xfce_def $TARGET/home/lenovo
	cp $cdrom/$xfce_empty $TARGET/home/lenovo
	cp $cdrom/$icaclient $TARGET/home/lenovo
	if [ "$client" = "vmware" ]; then
		cp $cdrom/$vminst $TARGET/home/lenovo && \
			chmod +x $TARGET/home/lenovo/$vminst
	fi
	if [ "$client" = "lidcc-edu" ]; then
		cp $cdrom/$bigagent $TARGET/home/lenovo
	fi
else
	wget $host/$firmfile && unxz -c $firmfile | ( cd $TARGET/lib/firmware; tar -xf - )
	wget $host/$xfce_def && cp $xfce_def $TARGET/home/lenovo
	wget $host/$xfce_empty && cp $xfce_empty $TARGET/home/lenovo
	wget $host/$icaclient && cp $icaclient $TARGET/home/lenovo
	if [ "$client" = "vmware" ]; then
		wget $host/$vminst && cp $vminst $TARGET/home/lenovo && \
			chmod +x $TARGET/home/lenovo/$vminst
	fi
	if [ "$client" = "lidcc-edu" ]; then
		wget $host/$bigagent && cp $bigagent $TARGET/home/lenovo
	fi
fi
#
mkdir $TARGET/var/log/journal
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
# set /etc/NetworkManager/NetworkManager.conf ethernet.wake-on-lan=g
#
netconfdir=$TARGET/etc/NetworkManager/conf.d
[ -d $netconfdir ] && cat > $netconfdir/999ethernet-wol.conf <<-EOD
	[connection-ethernet]
	ethernet.wake-on-lan=64
EOD
#
endline=123
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
remove_lidcc ()
{
	if dpkg --list lidc-client-edu; then
		dpkg --purge lidc-client-edu
	fi
	if dpkg --list lidc-client; then
		dpkg --purge lidc-client
	fi
	if dpkg --list jpeg-player; then
		dpkg --purge jpeg-player
	fi
	if dpkg --list virt-viewer; then
		dpkg --purge virt-viewer
	fi
}
#
purge_libreoffice ()
{
	apt-get update
	apt-get -y --allow-unauthenticated install lios-greeter-themes lenvdi-tools
	case "$vmhorizon" in
		"lidcc")
			if ! dpkg --list lidc-client
			then
				apt-get -y --allow-unauthenticated install lidc-client
			fi
			if ! dpkg --list virt-viewer
			then
				apt-get -y install virt-viewer
			fi
			;;
		"vmware")
			remove_lidcc
			install_vmhorizon $vminstf
			;;
		"citrix")
			remove_lidcc
			if ! dpkg --list ctxusb
			then
				apt-get -y --allow-unauthenticated install ctxusb
			fi
			;;
		"firefox")
			remove_lidcc
			;;
		"lidcc-edu")
			if ! dpkg --list lidc-client-edu
			then
				apt-get -y --allow-unauthenticated install lidc-client-edu jpeg-player
			fi
			if ! dpkg --list virt-viewer
			then
				apt-get -y install virt-viewer
			fi
			mkdir /home/lenovo/lidmagent
			pushd /home/lenovo/lidmagent
			tar -zxf $bigagent && ./lidmagent-setup.sh
			inst_status=$?
			popd
			[ $inst_status -eq 0 ] && rm -rf /home/lenovo/lidmagent
			;;
		*)
			echo "unknown vmhorizon value: $vmhorizon"
			exit 1
	esac
	sedsubs=
	[ -n "${lidm_s}" ] && sedsubs+="-e s/^#*LIDM=.*/LIDM=\"-s ${lidm_s}\"/ "
	[ -n "${lidm_p}" ] && sedsubs+="-e s/^#*PORT=.*/PORT=\"-p ${lidm_p}\"/ "
	[ -n "${sedsubs}" ] && eval sed -i ${sedsubs} /etc/default/plidm
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
lidm_s=192.168.98.104
lidm_p=7801
#
exec 1> /home/lenovo/rc-local.log 2>&1
#set -x
#
xfce_def=/home/lenovo/default-desktop.tar.xz
xfce_empty=/home/lenovo/empty-desktop.tar.xz
icaclient=/home/lenovo/icaclient.tar.xz
vminstf=/home/lenovo/VMware-Horizon-Client.x64.bundle
bigagent=/home/lenovo/lidmagent.tar.gz
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
chown $auto_user:$auto_user /home/$auto_user/.i18n
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
ulimit -c 819200
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
if dpkg --list icaclient; then
	autoapp=$appdesk/selfservice.desktop
	if systemctl --all list-units | fgrep ctxlogd > /dev/null 2>&1; then
		systemctl enable ctxlogd
	fi
	icaroot=/opt/Citrix/ICAClient
	[ -w ${icaroot}/config/module.ini ] && \
	sed -i -e '/^\[WFClient/aDesktopApplianceMode=TRUE' ${icaroot}/config/module.ini
	[ -r $autoapp ] && cp $autoapp /home/$auto_user/.config/autostart/
#
elif [ -r $appdesk/vmware-view.desktop ]; then
	cp $appdesk/vmware-view.desktop /home/$auto_user/.config/autostart/
	cp $appdesk/vmware-view.desktop /home/$auto_user/.config/$usrdesk
	cp $appdesk/vmware-view.desktop /home/lenovo/.config/$defdesk
#
elif dpkg --list lidc-client-edu; then
	if [ -r $appdesk/lidc-client-edu.desktop ]; then
		cp $appdesk/lidc-client-edu.desktop /home/$auto_user/.config/autostart/
		cp $appdesk/lidc-client-edu.desktop /home/$auto_user/.config/$usrdesk
		cp $appdesk/lidc-client-edu.desktop /home/lenovo/.config/$defdesk
	fi
elif dpkg --list lidc-client; then
	if [ -r $appdesk/lidc-client.desktop ]; then
		cp $appdesk/lidc-client.desktop /home/$auto_user/.config/autostart/
		cp $appdesk/lidc-client.desktop /home/$auto_user/.config/$usrdesk
		cp $appdesk/lidc-client.desktop /home/lenovo/.config/$defdesk
	fi
elif [ -f $appdesk/seturl.desktop ]; then
	cp $appdesk/exo-web-browser.desktop /home/$auto_user/.config/$usrdesk
	firstshot=.config/autostart/first-shot.desktop
	eval su - $auto_user -c \'"cp $appdesk/seturl.desktop $firstshot"\'
fi
#
rm -f $vminstf $icaclient $xfce_empty $xfce_def $bigagent
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
