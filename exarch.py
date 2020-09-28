#!/bin/python3 
#
import gzip
import os
import os.path
import sys

if len(sys.argv) < 3:
    print("Usage: {} source_pkg_desc dest_pkg_desc".format(sys.argv[0]))
    sys.exit(1)

spkg_file = sys.argv[1]
if not os.path.isfile(spkg_file):
    print("Missing package description file: {}".format(spkg_file))
    sys.exit(2)

dpkg_file = sys.argv[2]

fin = gzip.open(spkg_file, 'r')
fou = gzip.open(dpkg_file, 'w')

arch = ''
ignore = 0
idx = 0
lines = []
for sline in fin:
    mline = sline.decode('utf-8')
    idx = mline.find("Package:")
    if idx == 0:
        if arch != 'armhf' and arch != 'i386' and arch != 'armel' and ignore == 0:
            for ln in lines:
                fou.write(ln.encode('utf-8'))
        lines.clear()
        ignore = 0
    idx = mline.find("Architecture:")
    if idx == 0:
        arch = mline.split()[1]
    idx = mline.find("Filename:")
    if idx == 0:
        old_path = mline.split()[1]
        inter_dirs = old_path.split('/')
        if inter_dirs[0] == '.':
            inter_dirs = inter_dirs[1:]
        new_path = 'pool/inhouse/' + inter_dirs[0][0:1]
        old_path = 'cloudtimes'
        for dent in inter_dirs[0:-1]:
            new_path += '/' + dent
            old_path += '/' + dent
        deb_name = inter_dirs[-1]
        if arch != 'armhf' and arch != 'i386' and arch != 'armel':
            old_path += '/' + deb_name
            if not os.path.isfile(old_path):
                ignore = 1
                print("Warning! File: {} does not exist.".format(old_path))
            else:
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
                new_path += '/' + deb_name
                ndeb = open(new_path, 'wb')
                with open(old_path, 'rb') as ideb:
                    buf = ideb.read(4096)
                    while len(buf) > 0:
                        ndeb.write(buf)
                        buf = ideb.read(4096)
                ndeb.close()
                mline = "Filename: " + new_path + '\n'

    lines.append(mline)

fou.close()
fin.close()
sys.exit(0)
