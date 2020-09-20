#!/bin/bash
#
#
function try_get_pkg()
{
	pkgname=$1
	pattern="^$pkgname"
	if ! apt-cache search $pkgname | grep $pattern > /dev/null
	then
		echo "cannot find the package: \"$1\" on Internet"
		return
	fi
	h4w=${pkgname:0:4}
	if [ "${pkgname:0:3}" = "lib" ]
	then
		potdir=extra/$h4w
		[ -d $potdir ] || mkdir $potdir
	else
		potdir=extra/${pkgname:0:1}
		[ -d $potdir ] || mkdir $potdir
	fi
#
	pushd $potdir > /dev/null
	apt-get download $pkgname
	popd > /dev/null
}

#
[ -d extra ] || mkdir extra
#
dpkg --list | awk '/^ii/ {print $2}' | \
while read pkgname
do
	fname=$(find /media/cdrom -name ${pkgname%%:*}\* -print 2> /dev/null)
	if [ -z "$fname" ]
	then
		try_get_pkg "${pkgname%%:*}"
	fi
done
