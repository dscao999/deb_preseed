#!/bin/bash
#
TARGS=$(getopt -l mirror:,arch:,verbose,poweroff -o m:a:vp -- "$@")
[ $? -ne 0 ] && exit 1
#
HOST=ftp.us.debian.org
ARCH=amd64
VERBOSE=0
POWEROFF=0
eval set -- $TARGS
while true; do
	case "$1" in
	"--mirror")
		HOST=$2
		shift
		;;
	"--arch")
		ARCH=$2
		shift
		;;
	"--verbose")
		VERBOSE=1
		;;
	"--poweroff")
		POWEROFF=1;
		;;
	"--")
		shift
		break
		;;
	esac
	shift
done
#
gpg --no-default-keyring --keyring trustedkeys.gpg --import /usr/share/keyrings/debian-archive-keyring.gpg
#
# Known hosts of debian mirrors
#
#HOST=ftp.us.debian.org
#HOST=ftp2.cn.debian.org
#HOST=ftp.us.debian.org
#HOST=mirrors.tuna.tsinghua.edu.cn
#HOST=mirrors.ustc.edu.cn
#HOST=mirrors.163.com
#HOST=mirrors.huaweicloud.com
#DIST=buster,buster-updates,buster-backports
#
# regularly used arch
#
#ARCH=amd64,arm64,armhf
#
DEST=/var/www/html/debian
carch="${ARCH//,/ }"
incon=0
for march in $(ls -d $DEST/dists/buster/main/binary-*)
do
	sarch=${march##*-}
	[ "$sarch" = "all" ] && continue
	missing=1
	for narch in $carch
	do
		if [ "$sarch" == "$narch" ]
		then
			missing=0
			break
		fi
	done
	if [ $missing -eq 1 ]
	then
		echo "Arch \"$sarch\" from last run is misssing from current selection."
		incon=1
	fi
done
if [ $incon -eq 1 ]
then
	echo "Some archs from last run is missing from current selection."
	read -p "Continue? " ans
	if [ "x$ans" != "xY" ]
	then
		exit 5
	fi
	echo "Will continue updating using current selection."
	echo "	Some archs will be erased!"
fi
#
[ $VERBOSE -eq 1 ] && VERBOSE="--verbose --progress"
#
if ! mountpoint -q ${DEST}
then
	echo "${DEST} is not a mount point."
	exit 5
fi
#
DIST=buster,buster-backports,buster-updates
debmirror ${DEST} --host=${HOST} --method=http \
	--root=/debian --dist=${DIST} --di-dist=buster --di-arch=${ARCH} \
	--section=main,contrib,non-free --i18n --arch=${ARCH} \
	--nosource --postcleanup $VERBOSE
if [ $POWEROFF -eq 1 ]
then
	sudo systemctl poweroff
fi
