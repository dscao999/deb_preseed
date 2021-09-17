#!/usr/bin/python3
#
import os, sys, stat
import hashlib
import shutil
import subprocess as subp
from pathlib import Path

def manideb(debfile, arch):
    pkgdsc = []
    tmpot = '/tmp/depot'
    if os.path.isdir(tmpot):
        shutil.rmtree(tmpot)
    os.mkdir(tmpot)
    extract = 'dpkg-deb --raw-extract ' + debfile + ' ' + tmpot
    runstat = subp.run(extract, shell=True, text=True, stdout=subp.PIPE,
            stderr=subp.STDOUT)
    if runstat.returncode != 0:
        print(f'dpkg-deb --extract-raw {debfile} failed: {runstat.stdout}')
        return pkgdsc
    ctlfile = tmpot + '/DEBIAN/control'
    if not os.path.isfile(ctlfile):
        print(f'{debfile} missing control file.')
        return pkgdsc
    with open(ctlfile, "r") as fin:
        for ln in fin:
            ln = ln.rstrip('\n')
            pkgdsc.append(ln)
            recs = ln.split(':')
            if recs[0] == 'Description':
                break
            if recs[0] == 'Architecture' and recs[1].strip() != arch:
                print(f'Warning: {debfile} arch conflicts with its control file. {recs[1]} -- {arch}')

    shutil.rmtree(tmpot)
    return pkgdsc


if len(sys.argv) < 2:
    isotop = 'isotop'
else:
    isotop = sys.argv[1]

isotop = isotop.rstrip('/')
print(f'ISOTOP: {isotop}')
#
# check if this is an ISO top
#
try:
    info = isotop + '/.disk/info'
    with open(info, "r") as fin:
        ln = fin.read()
    if len(ln) == 0 or ln[:20] != 'Debian GNU/Linux 10.':
        print(f'Not a valid Debian 10 ISO top directory: {isotop}')
        sys.exit(1)
except:
    print(f'Not a valid Debian 10 ISO top directory: {isotop}')
    sys.exit(1)

dists = isotop + '/dists/lenvdi/main/'
if not os.path.isdir(dists):
    print(f'Directory {dists} does not exist.')
    sys.exit(2)
ost = os.stat(dists);
if ost.st_mode != (ost.st_mode|stat.S_IRWXU):
    os.chmod(dists, stat.S_IRWXU|ost.st_mode);

rel_pool = 'pool/lenvdi/'
pool = isotop + '/pool/lenvdi/'
if not os.path.isdir(pool):
    print(f'Directory {pool} does not exist.')
    sys.exit(3)

for binary in os.listdir(dists):
    bindir = dists + binary
    ost = os.stat(bindir)
    if ost.st_mode != (ost.st_mode|stat.S_IRWXU):
        os.chmod(dists + binary, ost.st_mode|stat.S_IRWXU)
    pkgfile = dists + binary + '/Packages'
    if os.path.isfile(pkgfile):
        print(f'os.remove({pkgfile})')
        os.remove(pkgfile)
    Path(pkgfile).touch()

deb_entries = os.listdir(pool)
for deb_entry in deb_entries:
    if deb_entry[-4:] != '.deb':
        continue
    arch = 'unknown'
    deb_arch = deb_entry.split('_')[-1]
    if deb_arch == 'all.deb':
        arch = 'all'
    elif deb_arch == 'amd64.deb':
        arch = 'amd64'
    elif deb_arch == 'arm64.deb':
        arch = 'arm64'
    elif deb_arch == 'armhf.deb':
        arch = 'armhf'
    if arch == 'unknown':
        print(f'DEB file {deb_entry} ignored.')
        continue

    debfile = pool + deb_entry
    print(f'Processing {debfile}...')
    fstat = os.stat(debfile)
    pkg_desc = manideb(debfile, arch)
    if len(pkg_desc) == 0:
        print(f'{debfile} no package info extracted.')
        continue
    pkg_desc.append('FileName: ' + rel_pool + deb_entry)
    pkg_desc.append('Size: ' + str(fstat.st_size))

    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(debfile, "rb") as fin:
        content = fin.read(8192)
        while content:
            md5.update(content)
            sha256.update(content)
            content = fin.read(8192)
    pkg_desc.append('MD5sum: ' + md5.hexdigest())
    pkg_desc.append('SHA256: ' + sha256.hexdigest())

    binary = dists + 'binary-' + arch
    if not os.path.isdir(binary):
        os.mkdir(binary, 0o755)
    pkgfile = binary + '/Packages'
    with open(pkgfile, "a") as fout:
        for ln in pkg_desc:
            fout.write(ln+'\n')
        fout.write('\n')

relfile = isotop + '/dists/lenvdi/Release'
if not os.path.isfile(relfile):
    print(f'Missing Release file {relfile}')
    sys.exit(5)

rel_prefix = isotop + '/dists/lenvdi/'
with open(relfile, "r") as fin:
    phrase = 0
    content = []
    for ln in fin:
        onsum = 0
        ln = ln.rstrip('\n')
        if ln[:7] == 'MD5Sum:':
            phrase = 5
            onsum = 1
        elif ln[:7] == 'SHA256:':
            phrase = 256
            onsum = 1
        if phrase == 0 or onsum == 1:
            content.append(ln)
            continue

        fields = ln.split()
        fname = rel_prefix + fields[2]
        fstat = os.stat(fname)
        fields[1] = fstat.st_size
        if phrase == 5:
            md5 = hashlib.md5()
            with open(fname, "rb") as hsin:
                for bln in hsin:
                    md5.update(bln)
            fields[0] = md5.hexdigest()
        elif phrase == 256:
            sha256 = hashlib.sha256()
            with open(fname, "rb") as hsin:
                for bln in hsin:
                    sha256.update(bln)
            fields[0] = sha256.hexdigest()
        content.append(' ' + fields[0] + f'{fields[1]:9d}' + ' ' + fields[2])

with open(relfile, "w") as fout:
    for ln in content:
        fout.write(ln + '\n')

sys.exit(0)
