#!/bin/bash
#
rootca=$1
if [ ! -f $rootca ]
then
	echo "Please specify your Root CA file in pem format."
	echo "Usage: $0 CA_File_Name"
	exit 1
fi
#
sudo cp $rootca /etc/ssl/certs/oVirt_rootca.pem
idxname=$(openssl x509 -noout -in $rootca -subject_hash)
cd /etc/ssl/certs
sudo ln -s oVirt_rootca.pem ${idxname}.0
