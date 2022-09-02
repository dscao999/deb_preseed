#!/usr/bin/python3
#
import os
import subprocess as subp
import gzip
import shutil

micmds = """for x in $(cat /proc/cmdline); do
    if [ "$x" = "stateless" ]; then
        cachedev=$(blkid|fgrep "LIOS_CACHE"|cut -d: -f1)
        [ -b "$cachedev" ] || break
        [ "$quiet" != "y" ] && log_begin_msg "Building Overlay RootFS"
        upd=root_upper
        lwd=root_lower
        mkdir /$upd /$lwd
        mkfs.xfs -L LIOS_CACHE -f $cachedev
        mount $cachedev /$upd
        mkdir /$upd/proc /$upd/dev /$upd/sys /$upd/run /$upd/work /$upd/root
        mount --move ${rootmnt} /$lwd
        mount -o remount -o ro /$lwd
        mount -t overlay -o lowerdir=/$lwd,upperdir=/$upd/root,workdir=/$upd/work root_overlay ${rootmnt}
        [ "$quiet" != "y" ] && log_begin_msg "Finish Building Overlay RootFS"
        break
    fi
done
"""
uid = os.getuid()
if uid != 0:
    print("root priviledge required")
    quit(1)

res = subp.run("findfs LABEL=LIOS_CACHE", shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT);
if res.returncode != 0:
    print(f"Cannot find cache partition: {res.stdout}");
    quit(2);

with open('/proc/cmdline', 'r') as fin:
    kparams = fin.read().split()
for param in kparams:
    if param.find('BOOT_IMAGE') == -1:
        continue
    idx = param.find('-')
    if idx == -1:
        print(f"Logici Error. Boot Image has no '-' character")
        quit(2)
    version = param[idx:]
    break

initramfs = '/boot/initrd.img' + version
if not os.path.isfile(initramfs):
    print(f"{initramfs} is not a regular file")
    quit(3)

troot = "./troot-" + str(os.getpid())
try:
    os.mkdir(troot, mode=0o755)
except:
    print(f'Cannot make new dir: {troot}')
    quit(4)

print(f"Expanding file: {troot}...")
owd = os.getcwd()
os.chdir(troot)
res = subp.run("gunzip -c " + initramfs + "|cpio -id", shell=True, text=True)
if res.returncode != 0:
    print(f"Failed to expand {initramfs}: {res.stdout}")
    quit(5)
try:
    shutil.copyfile('/usr/share/lentools/mkfs.xfs', './sbin/mkfs.xfs')
except:
    print("Cannot copy file /usr/share/lentools/mkfs.xfs")
    quit(6)
os.chmod('./sbin/mkfs.xfs', 0o755)

initfile = "init"
with open(initfile, "r") as fin:
    initcmds = fin.read().split('\n')
with open(initfile, "w") as fout:
    for ln in initcmds:
        fout.write(ln+'\n')
        if ln.find("maybe_break bottom") != 0:
            continue
        fout.write(micmds)
print("Assembling file: ../initramfs.img...")
res = subp.run("find . -print|cpio -o -H newc|gzip -c -9 > ../initramfs.img", shell=True, text=True)
os.chdir(owd)
if res.returncode != 0:
    print("Failed to assemble into file ../initramfs.img")
    quit(6)
print("Done")
#res = subp.run("mount -o remount -o rw /boot", shell=True)
#shutil.copyfile('initramfs.img', initramfs)
#res = subp.run("mount -o remount -o ro /boot", shell=True)
#os.remove("
