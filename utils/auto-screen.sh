#!/usr/bin/bash
#
LOGDIR=${PWD}/elog
[ -d $LOGDIR ] || mkdir $LOGDIR
sudo mount -o rw,nosuid,nodev,noexec,uid=1000,gid=1000 LABEL=WINDATA $LOGDIR
#
COMMAND=
OPTIONS=
ARGS=
if [ -r /etc/default/auto-screen ]
then
	. /etc/default/auto-screen
fi
if [ -z "$COMMAND" ]
then
	COMMAND="/usr/bin/firefox-esr"
	OPTIONS="--kiosk"
	ARGS="http://www.baidu.com"
fi
#
# wait for desktop
#
desktop=$(ps -ef|fgrep xfce4-session|fgrep -v grep)
while [ -z "$desktop" ]
do
	sleep 1
	desktop=$(ps -ef|fgrep xfdesktop|fgrep -v grep)
done
sleep 1
#
# execute the command
#
eval $COMMAND $OPTIONS $ARGS &
wait
sudo umount $LOGDIR
sudo systemctl poweroff
exit 0
