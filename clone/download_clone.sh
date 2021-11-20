#!/bin/sh -e
#
status=5
#
eval $(cat /proc/cmdline|sed -e s/auto//)
svrpot=$(dirname $url)
wget $svrpot/remote-clone.sh
chmod +x remote-clone.sh
netport=$(basename "$(ls -l /sys/class/net|fgrep -v virtual)")
macaddr=$(ip link show dev $netport|fgrep link/ether|cut -d/ -f2|cut -d' ' -f2|sed -e s/:/-/g)
wget $svrpot/conn.info
. ./conn.info
wget $svrpot/${KEY}
chmod u-x,go-rwx ${KEY}
if ! ssh -l $USER -i ${KEY} $SERVER "ls -ld $DEPOT"; then
	echo "No such directory: \"${DEPOT}\" at $SERVER"
	exit 11
fi
DEPOT=$DEPOT/$macaddr
if ssh -l $USER -i ${KEY} $SERVER "ls -ld $DEPOT"; then
	echo "Directory: \"${DEPOT}\" already exists at $SERVER"
	exit 12
fi
ssh -l $USER -i ${KEY} $SERVER "mkdir $DEPOT"
./remote-clone.sh --user $USER --server $SERVER --depot $DEPOT --key $KEY $ACTION
status=$?
echo "Exit code: $status"
exit $status
