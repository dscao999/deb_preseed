#!/usr/bin/python3
#
import os
import os.path

host_name_file = '/etc/hostname'
os_file = '/etc/os-release'
mem_file = '/proc/meminfo'
cpu_file = '/proc/cpuinfo'

def hostname():
    if not os.path.isfile(host_name_file):
        return ''
    with open(host_name_file, "r") as fin:
        line = fin.readline()
    return line.rstrip('\n')

def osname():
    if not os.path.isfile(os_file):
        return oinf
    with open(os_file, 'r') as fin:
        for line in fin:
            if line.find("PRETTY_NAME") > -1:
                break
    osdesc = line.split('=')[1]
    return osdesc.strip('"').rstrip('\n').rstrip('"')

def memsize():
    if not os.path.isfile(mem_file):
        return 0
    with open(mem_file, "r") as fin:
        for line in fin:
            if line.find("MemTotal") == 0:
                break
    mems = line.split()
    skb = int(mems[1])
    return int((skb - 1)/(1024*1024)) + 1

def cpuinfo():
    aimp = {0x41: 'ARM'}
    aarch = {8: 'AArch64'}
    apart = {0xd08: 'Cortex-A72', 0xd03: 'Cortex-A53', 0xd07: 'Cortex-A57'}

    def same_cpu(cpu1, cpu2):
        if len(cpu1) != len(cpu2):
            return False

        equal = True
        for key in cpu1.keys():
            if key.find('processor') != -1 or key.find('apicid') != -1 \
                    or key.find('cpu MHz') != -1 or key.find('core id') != -1 \
                    or key.find('siblings') != -1 or key.find('cpu cores') != -1:
                continue

            try:
                if cpu1[key] != cpu2[key]:
#                    print("Key: {}. Not Equal: {}---{}".format(key, cpu1[key], cpu2[key]))
                    equal = False
                    break
            except:
                equal = False
                break
        return equal


    cinfo = []
    with open(cpu_file, 'r') as fin:
        ncpu = {}
        for line in fin:
            if len(line.rstrip('\n')) == 0:
                if len(ncpu) > 0:
                    cinfo.append(ncpu)
                    ncpu = {}
                continue

            rec = line.rstrip('\n').split(': ')
            while len(rec[0]) > 0 and rec[0][-1] == '\t':
                rec[0] = rec[0].rstrip('\t')
            if len(rec[0]) > 0 and len(rec) > 1:
                ncpu[rec[0]] = rec[1]

    pcpu = {}
    numc = 0
    sorted_cinfo = []
    for cpu in cinfo:
        if not same_cpu(cpu, pcpu):
            if numc > 0:
                sorted_cinfo.append((pcpu, numc))
            pcpu = cpu
            numc = 1
        else:
            numc += 1
    if numc > 0:
        sorted_cinfo.append((pcpu, numc))

    cpu_infos = []
    for cpu_tup in sorted_cinfo:
        cpu_keys = cpu_tup[0].keys()
        if 'model name' in cpu_keys:
            cpu_infos.append((cpu_tup[0]['model name'], cpu_tup[1]))
            continue
        if 'CPU implementer' in cpu_keys:
            for key, val in cpu_tup[0].items():
                if key == 'CPU implementer':
                    c_vendor = aimp[int(val, 0)]
                if key == 'CPU architecture':
                    c_arch = aarch[int(val, 0)]
                if key == 'CPU part':
                    c_model = apart[int(val, 0)]
                if key == 'CPU revision':
                    c_rev = int(val, 0)
        cpu_infos.append((c_vendor+' '+c_arch+' '+c_model+' '+'Rev '+str(c_rev), cpu_tup[1]))
    return cpu_infos


if __name__ == '__main__':
    print("Host Name: {}".format(hostname()))
    osn = osname()
    print("OS: {}".format(osn))
    print("Memory Size: {}GiB".format(memsize()))
    cpuinfos = cpuinfo()
    for cpu in cpuinfos:
        print("Number of CPU: {} Type: {}".format(cpu[1], cpu[0]))
