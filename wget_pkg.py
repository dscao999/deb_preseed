#!/bin/python3
#
import sys
import gzip
import os.path
import subprocess
import wget

pkgname = ''
for mline in sys.stdin:
    if mline.find("Package:") == 0:
        pkgname = mline.split()[1]
    if mline.find("Versions:") == 0:
        break

if len(pkgname) == 0:
    print("Warning: No Package Information found")
    sys.exit(1)

location = sys.stdin.readline().split()[1]

prefix = '/var/lib/apt/lists/'
idx = location.index(prefix)
mpaths = location[idx+len(prefix):].rstrip(')').split('_')
url = "http:/"
for name in mpaths:
    url += '/' + name 
pkg_desc = mpaths[1]
for name in mpaths[2:]:
    pkg_desc += '_' + name

url += '.gz'
print("URL: {}".format(url))
pkg_desc += '.gz'
print("Package file: {}".format(pkg_desc))

if not os.path.isfile(pkg_desc):
    try:
        wget.download(url, pkg_desc)
    except:
        print("Fatal Error, Cannot download the file: {}".format(url))
        sys.exit(5)

pf = gzip.open(pkg_desc)
for bline in pf:
    mline = bline.decode('utf-8')
    if mline.find("Package:") == 0:
        cpkg = mline.split()[1]
        if cpkg != pkgname:
            continue
        else:
            break

if cpkg != pkgname:
    print("No package found.")
    sys.exit(2)

mf = gzip.open("Extra_Packages.gz", 'a')
mf.write(mline.encode('utf-8'))
for bline in pf:
    mline = bline.decode('utf-8')
    mf.write(mline.encode('utf-8'))
    if len(mline.rstrip()) == 0:
        break

mf.close()
pf.close()

sys.exit(0)
