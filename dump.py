import bvdf
import sys

if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2:
        print "Usage: python dump.py something.vdf"
    else:
        root = bvdf.get_root(args[1])
        root.decode()
        print root
