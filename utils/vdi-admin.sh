#!/bin/bash
#
TARGS=$(getopt -l client:,rootca:,sname:,sip:,ntp:,hostname: -o c:a:s:i:t -- "$@")
[ $? -ne 0 ] && exit 1
eval set -- $TARGS
HOSTNAME=
CLIENT=
SNAME=
SIP=
DNS=
ROOTCA=
#
HEND=0
while [ $HEND -eq 0 ]; do
	case "$1" in
	--hostname)
		HOSTNAME=$2
		shift
		;;
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
	ln -s $(basename ${ROOTCA}) ${idxname}.0
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
		sed -i -e "/^#*NTP=.*\$/s//NTP=$NTP/" /etc/systemd/timesyncd.conf
		[ $? -eq 0 ] && systemctl restart systemd-timesyncd
		;;
	setvdi)
		if [ -z "$SNAME" -o -z "$SIP" ]
		then
			echo "Missing server name, and/or server ip"
			exit 4
		fi
		eval sed -i -e "'/^[0-9].*[\\t ]${SNAME}/s/^./#&/'" \
			-e "'\$a#\n${SIP}\\t${SNAME}'" /etc/hosts
		;;
	set-hostname)
		ohostname=$(hostnamectl --static)
		if [ "$ohostname" != "$HOSTNAME" ]
		then
			sed -i -e "/${ohostname}/a127.0.1.1\t${HOSTNAME}" /etc/hosts
			hostnamectl --static set-hostname $HOSTNAME
			savelocal=rc.local-$$
			if [ -f /etc/rc.local ]
			then
				cp /etc/rc.local /etc/$savelocal
				cat >> /etc/rc.local <<-EOD
					sed -i -e "/${ohostname}\$/d" /etc/hosts
					rm /etc/rc.local
					[ -r /etc/$savelocal ] && mv /etc/$savelocal /etc/rc.local
				EOD
			else
				cat > /etc/rc.local <<-EOD
					#!/bin/bash
					sed -i -e "/${ohostname}\$/d" /etc/hosts
					rm /etc/rc.local
					[ -r /etc/$savelocal ] && mv /etc/$savelocal /etc/rc.local
				EOD
			fi
			chmod ugo+x /etc/rc.local
		fi
		;;
	*)
		echo "Unknown operation: $ACTION"
		exit 3
esac
