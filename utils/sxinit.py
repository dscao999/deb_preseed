#!/usr/bin/python3
#
import os, sys

home = "/home/user"
if not os.path.exists(home):
    print('Directory "{}" does not exist now.'.format(home))
    sys.exit(1)

with open(home+"/.xsessionrc", "w") as fout:
    fout.write('/usr/bin/auto-screen.sh > auto-screen.log 2>&1 &\n')

sys.exit(0)
