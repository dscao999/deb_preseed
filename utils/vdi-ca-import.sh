#!/bin/bash
#
TARGS=$(getopt -l client:,rootca:,sname:,sip:,dns -o c:a:s:i:d -- "$@")
[ $? -ne 0 ] && exit 1
eval set -- $TARGS
CLIENT=lidcc
SNAME=engine.cluster
SIP=169.1.1.1
DNS=
ROOTCA=
#
while true; do
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
	--dns)
		DNS=1
		;;
	--rootca)
		ROOTCA=$2
		shift
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
#  set up environment for service
#
function service_set()
{
if [ $DNS -eq 0 ]
then
	sed -i -e "\$a${SIP}\t${SNAME}" /etc/hosts
fi
}
#
# Import CA for ovirt
#
function ovirt_ca()
{
	cp $ROOTCA /etc/ssl/certs/oVirt_rootca.pem
	idxname=$(openssl x509 -noout -in $ROOTCA -subject_hash)
	cd /etc/ssl/certs
	ln -s oVirt_rootca.pem ${idxname}.0
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
		if dpkg --list lidc-client > /dev/null 2>&1
		then
			ovirt_ca
		else
			echo "No LIDC client is installed."
			exit 2
		fi
		;;
	citrix)
		if dpkg --list icaclient > /dev/null 2>&1
		then
			citrix_ca
		else
			echo "No Citrix Workspace App is installed."
			exit 2
		fi
		;;
	*)
		echo "CA for $CLIENT is not supported now."
		exit 1
		;;
	esac
}

case "$ACTION" in
	import_ca)
		import_ca()
		;;
	time_sync)
		;;
	set_service)
		;;
esac
