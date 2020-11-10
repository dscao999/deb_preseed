#!/bin/bash
#
action=$1
#
function extract()
{
	for debfile in $(ls -l *.deb|grep -E '^-r'|awk '{print $9}')
	do
		debdir=$(echo $debfile|cut -d_ -f1)
		[ -d "$debdir" ] && rm -rf "$debdir"
		echo "dpkg-deb --raw-extract $debfile $debdir"
		dpkg-deb --raw-extract "$debfile" "$debdir"
		sed -i -e /Installed-Size:/d $debdir/DEBIAN/control
	done
}

function add_size_statement()
{
	debdir=$1
	ts=$(du -sk $debdir|awk '{print $1}')
	t0=$(du -sk $debdir/DEBIAN|awk '{print $1}')
	sz=$((ts-t0))
	echo sed -i -e \"/Version.*\$/aInstalled-Size: $sz\" $debdir/DEBIAN/control
	sed -i -e "/Version.*\$/aInstalled-Size: $sz" $debdir/DEBIAN/control
#	sed -i -e "/Installed-Size/s/\///" $debdir/DEBIAN/control
}

[ -z "$action" ] && action=unknown

case "$action" in
"extract")
	extract
	;;
"add_size")
	for debdir in $(ls -ld *|grep -E '^dr'|awk '{print $9}')
	do
		add_size_statement "$debdir"
	done
	;;
"build-deb")
	for debdir in $(ls -ld *|grep -E '^dr'|awk '{print $9}')
	do
		debfile=$(ls ${debdir}_*.deb)
		[ -f $debfile ] || continue
		echo build deb: $debfile
		dpkg-deb --build $debdir $debfile
	done
	;;
*)
	echo "No such action: $action"
	;;
esac
