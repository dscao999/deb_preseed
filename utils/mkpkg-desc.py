#!/usr/bin/python3
#
import os, sys
import hashlib
import gzip, lzma
import shutil

fout = open("/tmp/Packages", "w")

debsink = "/tmp/pool/lenovo"
if not os.path.isdir(debsink):
    os.makedirs(debsink)
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
    debf = 'pool/lenovo/' + dent
    fout.write('Filename: ' + debf +'\n')
    fout.write('Size: '+str(os.path.getsize(dent))+'\n')
    debo = open('/tmp/' + debf, 'wb')
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

with open("/tmp/Packages", 'rb') as f_in:
    with gzip.open("/tmp/Packages.gz", 'wb') as gz_out:
        shutil.copyfileobj(f_in, gz_out);
    f_in.seek(0)
    with lzma.open("/tmp/Packages.xz", 'wb') as xz_out:
        shutil.copyfileobj(f_in, xz_out);

def hash_file(fname, hshname):
    hsh = hashlib.new(hshname)
    with open(fname, 'rb') as f_in:
        sl = f_in.read(8192)
        while sl:
            hsh.update(sl)
            sl = f_in.read(8192)
    return hsh.hexdigest()

print("MD5Sum:")
pkgname = "/tmp/Packages"
fsize = os.path.getsize(pkgname)
print((" " + hash_file(pkgname, 'md5') + ' {} {}').format(fsize, pkgname))
pkgname = "/tmp/Packages.gz"
fsize = os.path.getsize(pkgname)
print((" " + hash_file(pkgname, 'md5') + ' {} {}').format(fsize, pkgname))
pkgname = "/tmp/Packages.xz"
fsize = os.path.getsize(pkgname)
print((" " + hash_file(pkgname, 'md5') + ' {} {}').format(fsize, pkgname))

print("SHA256:")
pkgname = "/tmp/Packages"
fsize = os.path.getsize(pkgname)
print((" " + hash_file(pkgname, 'sha256') + ' {} {}').format(fsize, pkgname))
pkgname = "/tmp/Packages.gz"
fsize = os.path.getsize(pkgname)
print((" " + hash_file(pkgname, 'sha256') + ' {} {}').format(fsize, pkgname))
pkgname = "/tmp/Packages.xz"
fsize = os.path.getsize(pkgname)
print((" " + hash_file(pkgname, 'sha256') + ' {} {}').format(fsize, pkgname))

sys.exit(0)
