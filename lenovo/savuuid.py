#!/usr/bin/python3
#
import subprocess as subp
import sys

uidfile = "/etc/lios-uuid"

dmires = subp.run("dmidecode -t 1", text=True, shell=True, stdout=subp.PIPE, stderr=subp.STDOUT)
if dmires.returncode != 0:
    print(f"dmidecode failed: {dmires.returncode}. {dmires.stdout}")
    sys.exit(dmires.returncode)

res = dmires.stdout.split('\n')
uuid = 0
for ln in res:
    if ln.find("UUID:") != -1:
        uuid = 1
        break
if uuid == 0:
    print("No UUID found")
    sys.exit(10)
kval = ln.split()
if len(kval) != 2:
    print("dmidecode response syntax not recongnized")
    sys.exit(9)
with open(uidfile, "w") as fout:
    fout.write(kval[1]+'\n')
sys.exit(0)
