#!/usr/bin/python3
#
import sys, os, os.path, stat
import shutil, hashlib
import subprocess

import manipkg

def hash_file(pofile):
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(pofile, 'rb') as po:
        bytes = po.read()
    md5.update(bytes)
    sha256.update(bytes)
    return (md5.digest(), sha256.digest())

def add_deb(deb, isopool):
    pofile = isopool + '/' + os.path.basename(deb)
    shutil.copyfile(deb, pofile)
    debsiz = os.path.getsize(pofile)
    debdgst = hash_file(pofile)

    debdir = '/tmp/debpot'
    if os.path.exists(debdir):
        if os.path.isfile(debdir):
            os.remove(debdir)
        else:
            shutil.rmtree(debdir)

    extract = ['dpkg-deb', '--raw-extract', pofile, debdir]
    comp = subprocess.run(extract, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if comp.returncode != 0:
        print("Cannot extract the deb: {}".format(pofile))
        return

    ctlfile = debdir + '/DEBIAN/control'
    if not os.path.isfile(ctlfile):
        print("Invalid deb file: {}")
        return

    with open(ctlfile, "r") as ctl:
        ctl_lines = ctl.readlines()
    shutil.rmtree(debdir)

    sort_ctl = []
    for ln in ctl_lines:
        if ln.find('Package: ') == 0:
            pkgname = ln.split()[1].rstrip('\n')
            sort_ctl.append(ln)
            continue
        if ln.find('Version: ') == 0:
            pkgver = ln.split()[1].rstrip('\n')
            sort_ctl.append(ln)
            continue
        if ln.find('Source: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Priority: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Section: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Maintainer: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Architecture: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Breaks: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Replaces: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Recommends: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Conflicts: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Homepage: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Pre-Depends: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Tag: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Multi-Arch: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Depends:') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Installed-Size: ') == 0:
            sort_ctl.append(ln)
            continue
        if ln.find('Description: ') == 0:
            sort_ctl.append(ln)
            continue
    sort_ctl.append('FileName: pool/lenvdi/' + os.path.basename(deb) + '\n')
    sort_ctl.append('Size: ' + str(debsiz) + '\n')
    sort_ctl.append('MD5sum: ' + debdgst[0].hex() + '\n')
    sort_ctl.append('SHA256: ' + debdgst[1].hex() + '\n')

    print("Process Package: {}".format(pkgname))
    with open('/tmp/Package', 'w') as pkgw:
        for ln in sort_ctl:
            pkgw.write(ln)
    return (pkgname, pkgver, sort_ctl)

if len(sys.argv) < 3:
    print("Usage: {} debdir isodir".format(sys.argv[0]))
    sys.exit(1)

debdir = sys.argv[1]
isotop = sys.argv[2]
arch = 'amd64'
if len(sys.argv) > 3:
    arch = sys.argv[3]

if not os.path.isdir(debdir):
    print("{} is not a directory!".format(debdir))
    sys.exit(2)
if not os.path.isdir(isotop):
    print("{} is not a directory!".format(isotop))
    sys.exit(2)
#diskinfo = isotop + '/.disk/info'
#if not os.path.isfile(diskinfo):
#    print("'{}' is not a top directory for Debian ISO".format(isotop))
#    sys.exit(3)

#with open(diskinfo, 'r') as info:
#    ln = info.readlines()[0]
#if ln.find('Debian GNU/Linux') == -1:
#    print("{} is not a top directory for Debian 10 ISO")
#    sys.exit(4)

fmode = stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH
isopool = isotop + '/pool/lenvdi'
if not os.path.isdir(isopool):
    os.chmod(isotop+'/pool', fmode)
    os.makedirs(isopool)
isodist = isotop + '/dists/lenvdi/main/binary-' + arch
if not os.path.isdir(isodist):
    os.chmod(isotop+'/dists', fmode)
    os.makedirs(isodist)
pkgfile = isodist + '/Packages'
if not os.path.isfile(pkgfile):
    open(pkgfile, 'w').close()

tmpf = "/tmp/Packages.tmp"
entries = os.listdir(debdir)
for entry in entries:
    debfile = debdir + '/' + entry
    if not os.path.isfile(debfile):
        continue
    pkginfo = add_deb(debfile, isopool)
    if pkginfo:
        manipkg.pack_remove(pkgfile, tmpf, pkginfo[0], pkginfo[1])
        pout = open(tmpf, "a")
        for ln in pkginfo[2]:
            pout.write(ln)
        pout.write('\n')
        pout.close()
        shutil.copyfile(tmpf, pkgfile)

sys.exit(0)
