#!/bin/python3
#
import sys
import gzip
import os.path
import subprocess
import wget

def drain_stdin():
    for mline in sys.stdin:
        continue
    print('')

def download_deb(url_prefix, url_path):
    cpath = '.'
    dirs = url_path.split('/')
    for cwd in dirs[:-1]:
        cpath += '/' + cwd

    print("Local Path: {}".format(cpath))
    if not os.path.exists(cpath):
#        print("Will create dir: {}".format(cpath))
        os.makedirs(cpath)
    url = url_prefix + '/' + url_path
    local_file = cpath + '/' + dirs[-1]
    if not os.path.exists(local_file):
        try:
            wget.download(url, local_file)
#           print("Will download: {} to {}".format(url, local_file))
        except:
            print("Error, Cannot download {}".format(url, ))


pkgname = ''
for mline in sys.stdin:
    if mline.find("Package:") == 0:
        pkgname = mline.split()[1]
    if mline.find("Versions:") == 0:
        break

if len(pkgname) == 0:
    print("Warning: No Package Information found")
    drain_stdin()
    sys.exit(1)

location = sys.stdin.readline().split()[1]

prefix = '/var/lib/apt/lists/'
idx = location.index(prefix)
mpaths = location[idx+len(prefix):].rstrip(')').split('_')
url_prefix = "http://" + mpaths[0] + '/' + mpaths[1]
print("URL Prefix: {}".format(url_prefix))
url = "http:/"
for name in mpaths:
    url += '/' + name 
pkg_desc = mpaths[1]
for name in mpaths[2:]:
    pkg_desc += '_' + name

url += '.gz'
print("URL: {}".format(url))
pkg_desc += '.gz'

if not os.path.isfile(pkg_desc):
    try:
        wget.download(url, pkg_desc)
    except:
        print("Fatal Error, Cannot download the file: {}".format(url))
        drain_stdin()
        sys.exit(5)

pf = gzip.open(pkg_desc)
for bline in pf:
    mline = bline.decode('utf-8')
    if mline.find("Package:") == 0:
        cpkg = mline.split()[1]
        if cpkg == pkgname:
            break

if cpkg != pkgname:
    pf.close()
    print("No package found.")
    drain_stdin()
    sys.exit(2)

local_desc = "Extra_Packages.gz"
if os.path.isfile(local_desc):
    mf = gzip.open(local_desc, 'r')
    for nline in mf:
        oline = nline.decode('utf-8')
        if oline.find("Package:") == 0:
            opkg = oline.split()[1]
            if opkg == pkgname:
                print("Package {} already processed.".format(pkgname))
                mf.close()
                drain_stdin()
                sys.exit(0)
    mf.close()

mf = gzip.open(local_desc, 'a')
mf.write(mline.encode('utf-8'))
for bline in pf:
    mline = bline.decode('utf-8')
    idx = mline.find("Filename: ")
    if idx == 0:
        deb_url = url_prefix + '/' + mline.split()[1]
        download_deb(url_prefix, mline.split()[1])
    mf.write(mline.encode('utf-8'))
    if len(mline.rstrip()) == 0:
        break

mf.close()
pf.close()

drain_stdin()
sys.exit(0)
