#!/usr/bin/python3
#
import sys

def pack_remove(pkgf_in, pkgf_out, pkgname, pkgver):
    pout = open(pkgf_out, 'w')
    pin = open(pkgf_in, 'r')
 
    hitname = False
    for ln in pin:
        if ln.find("Package: ") == 0:
            pname = ln.split()[1].rstrip('\n')
            if pname == pkgname:
                hitname = True
                hitver = False
                pkgsav = []

        if not hitname:
            pout.write(ln)
            continue
            
        if not hitver:
            pkgsav.append(ln)

        if ln.find("Version: ") == 0:
            ver = ln.split()[1].rstrip('\n')
            if ver == pkgver:
                hitver = True
        if ln == '\n':
            if not hitver:
                for sln in pkgsav:
                    pout.write(sln)
            hitname = False

    pout.close()
    pin.close()

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: {} package_file package_name package_version".format(sys.argv[0]))
        sys.exit(1)
    pack_remove(sys.argv[1], "/tmp/Packages", sys.argv[2], sys.argv[3])
    sys.exit(0)
