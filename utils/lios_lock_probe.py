#!/usr/bin/python3
#
import os, sys
import subprocess as subp
#
# lios_probe hostname password
#
if len(sys.argv) < 3:
    print(f'Missing options. Usage: {sys.argv[0]} hostname password')
    sys.exit(1)

lockfile = '/run/lock/lios_probe_lock'
hostname = sys.argv[1]
password = sys.argv[2]

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
chpass = 'echo -n lenovo:' + password + '|chpasswd'
chret = subp.run(chpass, shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
if chret.returncode != 0:
    print(f'Cannot change password:\n{chret.stdout}')
    os.remove(lockfile)
    sys.exit(5)
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
    if hostname[-1] != '\n':
        hostname = hostname + '\n'
    fout.write(hostname)
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
