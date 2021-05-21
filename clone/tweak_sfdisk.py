#!/usr/bin/python3
#
import sys, os, os.path
import stat

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
mode = os.stat(sysdisk).st_mode
if not stat.S_ISBLK(mode):
    print("Device {} is not a block device.".format(sysdisk))
    sys.exit(1)

src_spec = ''
if argc > 2:
    src_spec = sys.argv[2]
if len(src_spec) == 0:
    print("Please specify the cloned image directory.")
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

partprefix = ''
if sysdisk[:9] == '/dev/nvme' or sysdisk[:8] == '/dev/mmc':
    partprefix = 'p'

sysdisk_size = 0
bname = sysdisk.split('/')[-1]
try:
    with open('/sys/block/'+bname+'/size', 'rb') as fin:
        sysdisk_size = int(fin.read())
except:
    print("Unable to get disk size: {}".format(sysdisk))
    sys.exit(6)

print("Disk Size: {}".format(sysdisk_size))

nlast_lba = sysdisk_size
olast_lba = 0
first_lba = 0
try:
    with open(src_spec + '/sys_disk_size.txt', 'rb') as fin:
        olast_lba = int(fin.read())
except:
    print("Unable to read disk size file")
    sys.exit(5)

def part_number(partdev):
    pseq=''
    for i in range(-1, -4, -1):
        digit = partdev[i]
        if digit < '0' or digit > '9':
            break
        pseq = digit + pseq
    return pseq

label = ''
odisk = 'x'
olen = len(odisk)
with open(src_spec + '/sys_disk_sfdisk.dat', "r") as fin:
    for ln in fin:
        fields = ln.split()
        if len(fields) == 0:
            sfout.write('\n')
            continue

        if fields[0] == 'label:':
            label = fields[-1]
        elif fields[0] == 'device:':
            odisk = fields[-1]
            olen = len(odisk)
            fields[-1] = sysdisk
        elif fields[0] == 'first-lba:':
            first_lba = int(fields[-1])
        elif fields[0] == 'last-lba:':
            olast_lba = int(fields[-1])
            nlast_lba = sysdisk_size - first_lba
            fields[-1] = str(nlast_lba)
        elif fields[0][:olen] == odisk:
            pseq = part_number(fields[0])
            fields[0] = sysdisk+partprefix+pseq
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
            if pstart + psize >= olast_lba - 2049:
                psize = nlast_lba - pstart
                fields[size_idx] = str(psize) + ','

        for field in fields:
            sfout.write(field)
            if field != fields[-1]:
                sfout.write(' ')
        sfout.write('\n')

sfout.close()

if len(sys.argv) > 4:
    osysparts = src_spec + '/sys_disk_partitions.txt'
    sysparts = sys.argv[4]
else:
    sys.exit(0)

if not os.path.isfile(osysparts):
    print("Clone image missing file: {}".format(osysparts))
    sys.exit(1)

try:
    sfout = open(sysparts, "w")
except:
    print("Cannot open file: {}".format(sysparts))
    exit(5)

with open(osysparts, "r") as fin:
    for ln in fin:
        fields = ln.split()
        if len(fields) == 0:
            sfout.write('\n')
        opart = fields[0][:-1]
        pseq = part_number(opart)
        fields[0] = sysdisk + partprefix + pseq + ':'
        for field in fields:
            sfout.write(field)
            if field != fields[-1]:
                sfout.write(' ')
        sfout.write('\n')
sfout.close()

sys.exit(0)
