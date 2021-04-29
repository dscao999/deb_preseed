#!/usr/bin/python3
#
import sys, os, os.path

argc = len(sys.argv)
sysdisk = ''
if argc > 1:
    sysdisk = sys.argv[1]
if len(sysdisk) == 0:
    print("Please specify a target disk.")
    sys.exit(1)
if not os.path.exists(sysdisk):
    print("Device does not exist: {}".format(sysdisk))
    sys.exit(1)
src_spec = ''
if argc > 2:
    src_spec = sys.argv[2]
if len(src_spec) == 0:
    print("Please specify a clone image directory.")
    sys.exit(1)
if not os.path.isdir(src_spec):
    print("Clone image directory: {} does not exist.".format(src_spec))
    sys.exit(1)
tar_spec = ''
if argc > 3:
    tar_spec = sys.argv[3]
if len(tar_spec) == 0:
    print("Please specify a sfdisk command file.")
    sys.exit(1)
try:
    sfout = open(tar_spec, "w")
except:
    print("Unable to open {} for writing.".format(tar_spec))
    sys.exit(7)

if sysdisk[:7] == '/dev/sd' or sysdisk[:7] == '/dev/hd':
    part = ''
elif sysdisk[:9] == '/dev/nvme' or sysdisk[:8] == '/dev/mmc':
    part = 'p'

sysdisk_size = 0
bname = sysdisk.split('/')[-1]
try:
    with open('/sys/block/'+bname+'/size', 'rb') as fin:
        sysdisk_size = int(fin.read())
except:
    print("Unable to get disk size: {}".format(sysdisk))
    sys.exit(6)

print("Disk size: {}".format(sysdisk_size))

try:
    with open(src_spec + '/sys_disk_size.txt', 'rb') as fin:
        olast_lba = int(fin.read())
except:
    print("Unable to read disk size file")
    sys.exit(7)

nlast_lba = sysdisk_size
first_lba = 0
odisk = 'x'
olen = len(odisk)
with open(src_spec + '/sys_disk_sfdisk.dat', "r") as fin:
    for ln in fin:
        fields = ln.split()
        if len(fields) == 0:
            sfout.write('\n')
            continue

        if fields[0] == 'device:':
            odisk = fields[-1]
            olen = len(odisk)
            fields[-1] = sysdisk
        elif fields[0] == 'first-lba:':
            first_lba = int(fields[-1])
        elif fields[0] == 'last-lba:':
            olast_lba = int(fields[-1])
            nlast_lba = sysdisk_size - first_lba
            fields[-1] = str(nlast_lba)
        if fields[0][:olen] == odisk:
            pseq = fields[0][-1]
            fields[0] = sysdisk+part+pseq
            idx = 0
            size_idx = 0
            pstart = 0
            psize = 0
            for field in fields:
                if field == 'start=':
                    pstart = int(fields[idx+1][:-1])
                elif field == 'size=':
                    psize = int(fields[idx+1][:-1])
                    size_idx = idx + 1
                idx += 1
            if pstart + psize + 2048 > olast_lba:
                psize = nlast_lba - pstart
                fields[size_idx] = str(psize) + ','

        for field in fields:
            sfout.write(field)
            if field != fields[-1]:
                sfout.write(' ')
        sfout.write('\n')

sfout.close()
sys.exit(0)
