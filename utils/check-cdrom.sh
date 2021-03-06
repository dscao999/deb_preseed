#!/bin/bash
#
dpkg --list | awk '/^ii/ {print $2}' | \
while read pkg_name
do
	pkg=${pkg_name%%:*}
	fname=$(find /media/cdrom -name ${pkg}\* -print 2> /dev/null)
	[ -z "$fname" ] || continue
	if ! apt-cache show $pkg > /dev/null 2>&1
	then
		echo "Critical Error: Cannot locate package: $pkg"
		continue
	fi
	apt-cache showpkg $pkg | python3 wget_pkg.py
done
