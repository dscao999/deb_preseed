#!/usr/bin/python3
#
import os, sys
import hashlib
import gzip, lzma
import shutil

if len(sys.argv) > 1:
    topdir = sys.argv[1]
    if topdir[-1] != '/':
        topdir = topdir + '/'
else:
    topdir = '/var/debmirror/lenvdi/'
if not os.path.isdir(topdir):
    print("DEB Dir not found: {}".format(topdir))
    sys.exit(1)

suite = topdir + 'dists/orca/'
if not os.path.isdir(suite):
    os.makedirs(suite)
binarch = suite + 'main/binary-arm64/'
if not os.path.isdir(binarch):
    os.makedirs(binarch)
pool = topdir + 'pool/lenovo/'
if not os.path.isdir(pool):
    os.makedirs(pool)

rel = suite + 'Release'
pkg = binarch + 'Packages'
fout = open(pkg, "w")

dents = os.listdir(".")
for dent in dents:
    if not os.path.isfile(dent):
        continue
    debdir = dent.split('_')[0]
    cntf = debdir + '/DEBIAN/control'
    if not os.path.isfile(cntf):
        print("Warning: {} has no DEBIAN/control.".format(debdir))
        continue
        
    with open(cntf, 'r') as cfin:
        afd = False
        for ln in cfin:
            if afd and ln.find(':') == -1:
                continue
            afd = False
            fout.write(ln)
            if ln.find('Description: ') == 0:
                afd = True

    fout.write('Priority: required\n')
    debf = pool + dent
    fout.write('Filename: ' + debf +'\n')
    fout.write('Size: '+str(os.path.getsize(dent))+'\n')
    debo = open(debf, 'wb')
    md5 = hashlib.new('md5')
    sha = hashlib.new('sha256')
    with open(dent, 'rb') as debin:
        sl = debin.read(8192)
        while sl:
            md5.update(sl)
            sha.update(sl)
            debo.write(sl)
            sl = debin.read(8192)
    debo.close()
    fout.write('MD5sum: '+md5.hexdigest()+'\n')
    fout.write('SHA256: '+sha.hexdigest()+'\n')
    fout.write('\n')

fout.close()

with open(pkg, 'rb') as f_in:
    with gzip.open(pkg+".gz", 'wb') as gz_out:
        shutil.copyfileobj(f_in, gz_out);
    f_in.seek(0)
    with lzma.open(pkg+".xz", 'wb') as xz_out:
        shutil.copyfileobj(f_in, xz_out);

def hash_file(fname, hshname):
    hsh = hashlib.new(hshname)
    with open(fname, 'rb') as f_in:
        sl = f_in.read(8192)
        while sl:
            hsh.update(sl)
            sl = f_in.read(8192)
    return hsh.hexdigest()

binrel = """Archive: orca
Origin: Lenovo
Label: Lenovo
Version: 0.11
Acquire-By-Hash: yes
Component: main
Architecture: arm64"""

dstrel = """Origin: Lenovo
Label: Lenovo
Suite: orca
Codename: orca
Date: Wed, 04 Nov 2020 20:15:10 UTC
Valid-Until: Wed, 11 Nov 2020 20:15:10 UTC
Architectures: arm64
Components: main
Description: VDI Components for LIOS"""

with open(binarch + "Release", "w") as fo:
    fo.write(binrel)
with open(suite + "Release", "w") as fo:
    fo.write(dstrel)

    fo.write("MD5Sum:\n")
    pkgname = pkg
    fsize = os.path.getsize(pkgname)
    mp = len(suite)
    fo.write(" " + hash_file(pkgname, 'md5') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')
    pkgname = pkg + ".gz"
    fsize = os.path.getsize(pkgname)
    fo.write(" " + hash_file(pkgname, 'md5') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')
    pkgname = pkg + ".xz"
    fsize = os.path.getsize(pkgname)
    fo.write(" " + hash_file(pkgname, 'md5') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')
    pkgname = binarch + "Release"
    fsize = os.path.getsize(pkgname)
    fo.write(" " + hash_file(pkgname, 'md5') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')

    fo.write("SHA256:\n")
    pkgname = pkg
    fsize = os.path.getsize(pkgname)
    fo.write(" " + hash_file(pkgname, 'sha256') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')
    pkgname = pkg + ".gz"
    fsize = os.path.getsize(pkgname)
    fo.write(" " + hash_file(pkgname, 'sha256') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')
    pkgname = pkg + ".xz"
    fsize = os.path.getsize(pkgname)
    fo.write(" " + hash_file(pkgname, 'sha256') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')
    pkgname = binarch + "Release"
    fsize = os.path.getsize(pkgname)
    fo.write(" " + hash_file(pkgname, 'sha256') + ' ' + str(fsize) + ' '
            + pkgname[mp:] + '\n')

sys.exit(0)
