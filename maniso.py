#!/usr/bin/python3
#
import os, sys, stat
import shutil
import tkinter as tk

mfont = ('courier', 16, 'bold')

def pre_check(isodir):
    isodir = isodir.rstrip('/')
    if not os.path.ismount(isodir):
        print("Error: {} is not a mount point.".format(isodir))
        sys.exit(1)
    info = isodir + '/.disk/info'
    if not os.path.isfile(info):
        print("Error: {} is not a LIOS ISO image.".format(isodir))
        sys.exit(2)
    with open(info, 'r') as inf:
        label = inf.read()
        if label.find('Lenovo LIOS') != 0:
            print("Error: {} is not an legitimate LIOS image.".format(isodir))
            sys.exit(3)

def remove_rdonly(func, path, _):
    st = os.stat(path, follow_symlinks=False)
    if (st.st_mode & stat.S_IWRITE) == 0:
        os.chmod(path, stat.S_IWRITE|st.st_mode)
    dr = os.path.dirname(path)
    st = os.stat(dr, follow_symlinks=False)
    if (st.st_mode & stat.S_IWRITE) == 0:
        os.chmod(dr, st.st_mode|stat.S_IWRITE)
    func(path)

def parse_preseed(rootdev, clock_setup, time_svr):
    seed = topdir + '/preseed/ubuntu-server.seed'
    inf = open(seed, 'r')
    line = inf.readline()
    while len(line) > 0:
        lns = line.split()
        if len(lns) < 4:
            line = inf.readline()
            continue

        if lns[0] == "partman-auto" and lns[1] == "partman-auto/disk" and lns[2] == "string":
            rootdev = lns[3]
        elif lns[0] == "d-i" and lns[1] == "clock-setup/ntp-server" and lns[2] == "string":
            time_svr = lns[3]
        elif lns[0] == "d-i" and lns[1] == "clock-setup/ntp" and lns[2] == "boolean":
            if lns[3] == "true":
                clock_setup = True

        line = inf.readline()
    inf.close()

class RootDev_Disp(tk.Frame):
    def __init__(self, parent, rootdev):
        super().__init__(parent)
        uf = tk.Frame(self)
        uf.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)
        rdev_label = tk.Label(uf, text="root device:", font=mfont)
        rdev_label.pack(side=tk.LEFT)
        self.rdev_text = tk.Entry(uf, font=mfont)
        self.rdev_text.insert(0, rootdev)
        self.rdev_text.pack(side=tk.RIGHT)
        lf = tk.Frame(self, height=2, bd=1, bg='red', relief=tk.SUNKEN)
        lf.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

    def pack(self, **kargs):
        super().pack(**kargs)

    def get_rootdev(self):
        return self.rdev_text.get()

class ClockSet_Disp(tk.Frame):
    def __init__(self, parent, settm, ntpip):
        super().__init__(parent)
        self.ntpip = ntpip
        self.set_clock = tk.IntVar()
        if settm:
            self.set_clock.set(1)
        else:
            self.set_clock.set(0)
        chk_clock = tk.Checkbutton(self, text="Set Clock", variable=self.set_clock,
                font=mfont, command=self.clock_check)
        chk_clock.pack()
        lf = tk.Frame(self)
        lf.pack(fill=tk.X, expand=tk.YES)
        ntp_label = tk.Label(lf, text="NTP Server:", font=mfont)
        ntp_label.pack(side=tk.LEFT)
        self.ntp_ip = tk.Entry(lf, font=mfont)
        if self.set_clock.get() == 1:
            self.ntp_ip.insert(0, time_svr)
        else:
            self.ntp_ip.config(state='disabled')
        self.ntp_ip.pack(side=tk.RIGHT)
        lf = tk.Frame(self, height=2, bd=1, bg='red', relief=tk.SUNKEN)
        lf.pack(fill=tk.X, padx=5, pady=5)

    def pack(self, **kargs):
        super().pack(**kargs)

    def clock_check(self):
        chk = self.set_clock.get()
        if chk == 1:
            self.ntp_ip.config(state='normal')
        else:
            self.ntp_ip.config(state='disabled')

    def get_clock_set(self):
        chk = self.set_clock.get()
        if chk == 0:
            return ''
        else:
            return self.ntp_ip.get()

if len(sys.argv) < 2:
    print("Error: An LIOS ISO mount point must be specified.")
    sys.exit(5)

isodir = sys.argv[1]
topdir = "isotop-"+str(os.getpid())

pre_check(isodir)

#shutil.copytree(isodir, topdir, symlinks=True)

rootdev = ''
time_svr = ''
clock_setup = False

#parse_preseed(rootdev, clock_setup, time_svr)

#if len(rootdev) == 0:
#    print("No Root Device, Invalid LIOS ISO.")
#    print("Deleting working space. Please wait for a while...")
#    shutil.rmtree(topdir, onerror=remove_rdonly)
#    sys.exit(6)

root = tk.Tk()
#root.title(sys.argv[0])
root.wm_title(sys.argv[0])

rdev_disp = RootDev_Disp(root, rootdev)
rdev_disp.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)

clock_disp = ClockSet_Disp(root, clock_setup, time_svr)
clock_disp.pack(side=tk.BOTTOM, expand=tk.YES, fill=tk.X)

root.mainloop()

print("Deleting working space. Please wait for a while...")
#shutil.rmtree(topdir, onerror=remove_rdonly)
sys.exit(0)
