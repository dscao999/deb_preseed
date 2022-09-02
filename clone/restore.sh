#!/bin/bash
#
while ! mountpoint -q /usr/lib/live/mount/medium; do
	sleep 3
done
#
mount -o ro -t squashfs /usr/lib/live/mount/medium/live/cloned_images.squashfs /var/www/html/debian/
#
clone.sh restore <<-EOD
1
Y
1
Y
EOD
#
sync
systemctl reboot
