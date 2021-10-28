#use command line install mode
cmdline
# accept license
eula --agreed
# System authorization information
auth --enableshadow --passalgo=sha512
# Use Live Image installation media
liveimg --url=file:///run/install/repo/ovirt-node-ng-image.squashfs.img
# Use graphical install
graphical
# Keyboard layouts
keyboard --vckeymap=us --xlayouts='us'
# System language
lang en_US.UTF-8
# System timezone
timezone Asia/Shanghai --isUtc --nontp
# Root password
rootpw --iscrypted $6$RKC5W15k3K/cXBJf$4rEaKMZF/EtjIl0zZvjpGeZJjFlYpKzy76svDzH2DaDRE7XTADpiSvUMARYj0Zcsqay9RjI4UOFr7djw34XHR1
# System services
services --enabled="chronyd"
# User Information and password
user --groups=wheel --name=lenovo --password=$6$dBtyehHvnQ6ss$VhiwJ1ISBLZvdnudHjvrglTCcvTkJovn8cNXS9G.BvolZBlBmUOqBrxqUvtpWVL2NRSCzKp8K1obYMgKgcMvD/ --iscrypted --gecos="Lenovo Administrator"

# Network information
network --device=admin --activate --bootproto=static --ip=$admin_ip --netmask=255.255.255.0 --nodefroute --nodns --noipv6 --teamslaves="$admin_port1'{\"prio\":-10, \"sticky\": true}',$admin_port2'{\"prio\":100}' --teamconfig="{\"runner\": {\"name\": \"activebackup\"}}"
network --device=gluster --activate --bootproto=static --ip=$gluster_ip --netmask=255.255.255.0 --nodefroute --nodns --noipv6 --teamslaves="$gluster_port1'{\"prio\":-10, \"sticky\": true}',$gluster_port2'{\"prio\":100}' --teamconfig="{\"runner\": {\"name\": \"activebackup\"}}"
network --hostname=$namezeus
# disable firewall and selinux
firewall --disabled
selinux --disabled
#

# ignore all other disks
ignoredisk --only-use=$rootdisk
# System bootloader configuration
bootloader --append=" crashkernel=auto" --location=mbr --boot-drive=$rootdisk
# Partition clearing information
clearpart --all --initlabel --drives=$rootdisk
# Disk partitioning information
part /boot/efi --fstype="efi" --ondisk=$rootdisk --size=200 --label="EFI_SP"
part /boot --fstype="ext2" --ondisk=$rootdisk --size=1024 --label="BOOTFS"
#
part pv.407 --fstype="lvmpv" --ondisk=$rootdisk --size=70000 --grow
volgroup onn_$namezeus --pesize=4096 pv.407
logvol none  --fstype="None" --size=60000 --thinpool --metadatasize=4096 --chunksize=65536 --name=pool00 --vgname=onn_$namezeus
#
logvol swap  --fstype="swap" --size=1024  --label="SWAP" --name=swap --vgname=onn_$namezeus
logvol /     --fstype="xfs" --size=10240  --label="ROOTFS" --thin --poolname=pool00 --name=root --vgname=onn_$namezeus
logvol /var  --fstype="xfs" --size=10240  --label="VARFS"  --thin --poolname=pool00 --name=var  --vgname=onn_$namezeus
logvol /home  --fstype="xfs" --size=1024 --label="HOMEFS" --thin --poolname=pool00 --name=home --vgname=onn_$namezeus
logvol /tmp   --fstype="xfs" --size=1024 --label="TMPFS"  --thin --poolname=pool00 --name=tmp  --vgname=onn_$namezeus
#
logvol /var/log   --fstype="xfs" --size=8192  --label="LOGFS"  --thin --poolname=pool00 --name=var_log  --vgname=onn_$namezeus
logvol /var/log/audit --fstype="xfs" --size=2048 --label="AUDITFS" --thin --poolname=pool00 --name=var_log_audit --vgname=onn_$namezeus

%post --erroronfail
imgbase layout --init

[ -d /etc/multipath/conf.d ] || mkdir -p /etc/multipath/conf.d
cat > /etc/multipath/conf.d/usb-storage.conf <<EOD
blacklist {
	property "ID_USB_INTERFACE_NUM"
	property "ID_CDROM"
}
EOD

%end

%anaconda
pwpolicy root --minlen=6 --minquality=1 --notstrict --nochanges --notempty
pwpolicy user --minlen=6 --minquality=1 --notstrict --nochanges --emptyok
pwpolicy luks --minlen=6 --minquality=1 --notstrict --nochanges --notempty
%end

%pre --interpreter=/usr/bin/python
import os

def lsdisk():
    tpath = '/dev/disk/by-path'
    with os.scandir(tpath) as lndevs:
        devpairs = [('None', 'None')]
        for lndev in lndevs:
            pname = lndev.name
            if not lndev.is_symlink():
                continue
            part = pname.find("-part")
            usb = pname.find("usb")
            if part != -1 or usb != -1:
                continue

            tname = os.readlink(tpath+'/'+pname)
            slash = tname.rfind('/')
            if slash != -1:
                tname = tname[slash+1:]
            curtup = (pname, '/dev/'+tname)
            skip = 0
            for tup in devpairs:
                if tup == curtup:
                    skip = 1
                    break
            if skip == 1:
                continue
            devpairs.append(curtup)
    return devpairs

ks_proto = \
"""
"""

with open('/tmp/custom.ks', 'w') as ks:
	ks.write('network  --hostname=zeus05\n')
	ks_proto = ks_proto.replace('$rootdisk', 'vda')
	ks_proto = ks_proto.replace('$namezeus', 'zeus05')
	ks.write(ks_proto)
exit(0)
%end
