import bvdf
import sys

if __name__ == '__main__':
    args = sys.argv
    if len(args) != 3:
        print "Usage: python search.py appinfo.vdf gameid (e.g. 400)"
    else:
        root = bvdf.AppInfoFile(path = args[1])
        root.full_decode = False
        root.read_header()
        for c in root.read_children():
            if c['id'] == int(args[2]):
                c.data['children'] = c.read_children()
                print c
