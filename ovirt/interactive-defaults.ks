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
user --groups=wheel --name=dscao --password=$6$dBtyehHvnQ6ss$VhiwJ1ISBLZvdnudHjvrglTCcvTkJovn8cNXS9G.BvolZBlBmUOqBrxqUvtpWVL2NRSCzKp8K1obYMgKgcMvD/ --iscrypted --gecos="Dashi Cao"

# Network information
network  --bootproto=static --device=eth0 --onboot=off --ipv6=auto --no-activate
network  --hostname=zeus01

selinux --disabled
#
ignoredisk --only-use=vda
# System bootloader configuration
bootloader --append=" crashkernel=auto" --location=mbr --boot-drive=vda
# Partition clearing information
clearpart --all --initlabel --drives=vda
# Disk partitioning information
part /boot/efi --fstype="efi" --ondisk=vda --size=200 --label="EFI_SP"
part /boot --fstype="ext2" --ondisk=vda --size=1024 --label="BOOTFS"
#
part pv.407 --fstype="lvmpv" --ondisk=vda --size=50000 --grow
volgroup onn_zeus01 --pesize=4096 pv.407
logvol none  --fstype="None" --size=30720 --thinpool --metadatasize=4096 --chunksize=65536 --name=pool00 --vgname=onn_zeus01
#
logvol swap  --fstype="swap" --size=1024  --label="SWAP" --name=swap --vgname=onn_zeus01
logvol /     --fstype="xfs" --size=10240  --label="ROOTFS" --thin --poolname=pool00 --name=root --vgname=onn_zeus01
logvol /var  --fstype="xfs" --size=10240  --label="VARFS"  --thin --poolname=pool00 --name=var  --vgname=onn_zeus01
logvol /home  --fstype="xfs" --size=1024 --label="HOMEFS" --thin --poolname=pool00 --name=home --vgname=onn_zeus01
logvol /tmp   --fstype="xfs" --size=1024 --label="TMPFS"  --thin --poolname=pool00 --name=tmp  --vgname=onn_zeus01
#
logvol /var/log   --fstype="xfs" --size=8192  --label="LOGFS"  --thin --poolname=pool00 --name=var_log  --vgname=onn_zeus01
logvol /var/log/audit --fstype="xfs" --size=2048 --label="AUDITFS" --thin --poolname=pool00 --name=var_log_audit --vgname=onn_zeus01

%post --erroronfail
imgbase layout --init
%end

%anaconda
pwpolicy root --minlen=6 --minquality=1 --notstrict --nochanges --notempty
pwpolicy user --minlen=6 --minquality=1 --notstrict --nochanges --emptyok
pwpolicy luks --minlen=6 --minquality=1 --notstrict --nochanges --notempty
%end
