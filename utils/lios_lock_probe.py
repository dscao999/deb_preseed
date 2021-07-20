#!/usr/bin/python3
#
import argparse
import os, sys
import subprocess as subp
import argparse
#
# lios_probe --hostname hostname --password password
#
parser = argparse.ArgumentParser()
parser.add_argument('--hostname', help='new hostname')
parser.add_argument('--password', help='new password')
parser.add_argument('--username', default='lenovo', help='user name')
args = parser.parse_args()

lockfile = '/run/lock/lios_probe_lock'
hostname = ''
if args.hostname:
    hostname = args.hostname
password = ''
if args.password:
    password = args.password
username = args.username

try:
    fd = os.open(lockfile, os.O_WRONLY|os.O_CREAT|os.O_EXCL)
except:
    print(f'Failed to accquire the lock: {lockfile}')
    sys.exit(2)
fobj = os.fdopen(fd, 'w')
fobj.write(hostname)
fobj.close()
#
# change user password
#
if len(password) > 0:
    chpass = 'echo -n ' + username + ':' + password + '|chpasswd'
    chret = subp.run(chpass, shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
    if chret.returncode != 0:
        print(f'Cannot change password:\n{chret.stdout}')
        os.remove(lockfile)
        sys.exit(5)
#
if len(hostname) == 0:
    os.remove(lockfile)
    sys.exit(0)
#
# change hostname
#
with open('/etc/hostname', 'r') as fin:
    ohostname = fin.read()
ohostname = ohostname.rstrip('\n')
nln = []
with open('/etc/hosts', 'r') as fin:
    for ln in fin:
        fields = ln.split()
        if len(fields) > 0 and fields[0] == '127.0.1.1':
            nln.append('127.0.1.1\t' + hostname + '\n')
        nln.append(ln)
with open('/etc/hosts', 'w') as fout:
    for ln in nln:
        fout.write(ln)
reboot = False
modcmd = 'hostnamectl set-hostname ' + hostname
modret = subp.run(modcmd, shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
if modret.returncode != 0:
    print(f'shell command failed: {modret.stdout}')
    reboot = True
with open('/etc/hostname', 'w') as fout:
    fout.write(hostname+'\n')
#
with open('/etc/hosts', 'w') as fout:
    for ln in nln:
        fields = ln.split()
        if len(fields) > 1 and fields[1] == ohostname:
            continue
        fout.write(ln)

# remove lock and return
os.remove(lockfile)
if reboot:
    subp.run("systemctl reboot", shell=True)
sys.exit(0)
