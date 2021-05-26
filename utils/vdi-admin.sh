#!/bin/bash
#
TARGS=$(getopt -l client:,rootca:,sname:,sip:,ntp: -o c:a:s:i:t -- "$@")
[ $? -ne 0 ] && exit 1
eval set -- $TARGS
CLIENT=
SNAME=
SIP=
DNS=
ROOTCA=
#
HEND=0
while [ $HEND -eq 0 ]; do
	case "$1" in
	--client)
		CLIENT=$2
		shift
		;;
	--sname)
		SNAME=$2
		shift
		;;
	--sip)
		SIP=$2
		shift
		;;
	--ntp)
		NTP=$2
		shift
		;;
	--rootca)
		ROOTCA=$2
		shift
		;;
	--)
		HEND=1
		;;
	*)
		echo "Unknown option: $1"
		exit 1
		;;
	esac
	shift
done
#
ACTION=$1
#
# Import CA for ovirt
#
function ovirt_ca()
{
	cp $ROOTCA /etc/ssl/certs/
	idxname=$(openssl x509 -noout -in $ROOTCA -subject_hash)
	cd /etc/ssl/certs
	ln -s ${ROOTCA} ${idxname}.0
	cd -
}
#
# Import CA for Citrix workspace app
#
function citrix_ca()
{
	icaroot=/opt/Citrix/ICAClient
	cp $ROOTCA ${icaroot}/keystore/cacerts/
	${icaroot}/util/ctx_rehash
}
#
#  Import CA
#
function import_ca()
{
	if [ -z "$ROOTCA" -o ! -f $ROOTCA ]
	then
		echo "Please specify your Root CA file in pem format."
		echo "Usage: $0 CA_File_Name"
		exit 1
	fi
#
	case "$CLIENT" in
	lidcc)
		ovirt_ca
		;;
	citrix)
		citrix_ca
		;;
	*)
		echo "CA for $CLIENT is not supported now."
		exit 1
		;;
	esac
}

case "$ACTION" in
	import_ca)
		import_ca
		;;
	time_sync)
		if [ -z "$NTP" ]
		then
			echo "Empty NTP server string."
			exit 2
		fi
		sed -e "/^NTP=.*\$/s//NTP=$NTP/" /etc/systemd/timesyncd.conf
		[ $? -eq 0 ] && systemctl restart systemd-timesyncd
		;;
	setvdi)
		if [ -z "$SNAME" -o -z "$SIP" ]
		then
			echo "Missing server name, and/or server ip"
			exit 4
		fi
		eval sed -e "'/^[0-9].* [\\t ]${SNAME}/s/^./#&/'" \
			-e "'\$a${SIP}\\t${SNAME}'" /etc/hosts
		;;
	*)
		echo "Unknown operation: $ACTION"
		exit 3
esac
