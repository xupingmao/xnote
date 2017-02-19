from BaseHandler import *
from io import StringIO
from io import BytesIO
import re

HEX_MAP = {
    0: '0',
    1: '1',
    2: '2',
    3: '3',
    4: '4',
    5: '5',
    6: '6',
    7: '7',
    8: '8',
    9: '9',
    10: 'a',
    11: 'b',
    12: 'c',
    13: 'd',
    14: 'e',
    15: 'f'
}

HEX_MAP_REV = {
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    'a': 10,
    'b': 11,
    'c': 12,
    'd': 13,
    'e': 14,
    'f': 15,
}

"""
add additional index file may be better
"""

class handler(BaseHandler):

    def encode(self, string):
        bytes = string.encode("utf-8")
        buf = StringIO()
        for b in bytes:
            b1 = b >> 4
            b2 = b & 0x0f
            buf.write(HEX_MAP[b1])
            buf.write(HEX_MAP[b2])
        buf.seek(0)
        return buf.read()

    def decode(self, string):
        byte_list = []
        for i in range(0, len(string), 2):
            c1 = string[i];
            c2 = string[i+1];
            b1 = HEX_MAP_REV[c1]
            b2 = HEX_MAP_REV[c2]
            byte_list.append((b1 << 4) + b2)
        buf = bytes(byte_list)
        return buf.decode("utf-8")

    def restore(self, root):
        parent = root
        for path in os.listdir(parent):
            abspath = os.path.join(parent, path)
            # if os.path.isdir(abspath):
            #     # self.protect(abspath)
            #     continue
            # else:
            new_name = self.decode(path)
            newpath = os.path.join(parent, new_name)
            if os.path.exists(newpath):
                logger.warn("{} already exists", newpath)
                continue
            os.rename(abspath, newpath)

    def protect(self, root):
        parent = root

        encoded = True
        # check first
        p = re.compile(r'[0-9a-f]+')
        for path in os.listdir(parent):
            if len(path) % 2 != 0:
                encoded = False
                break
            if not p.match(path):
                encoded = False
                break

        if encoded:
            return self.restore(root)

        transit_map = {}

        for path in os.listdir(parent):
            abspath = os.path.join(parent, path)
            # if os.path.isdir(abspath):
                # self.protect(abspath)
            #     continue
            # else:
            new_name = self.encode(path)
            newpath = os.path.join(parent, new_name)

            transit_map[abspath] = newpath
            
            if os.path.exists(newpath):
                logger.warn("{} already exists", newpath)
                continue
            os.rename(abspath, newpath)

        # transit here
        rollback_map = {}
        try:
            for oldpath in transit_map:
                os.rename(oldpath, newpath)
                rollback_map[newpath] = oldpath
        except:
            for newpath in rollback_map:
                oldpath = rollback_map[newpath]
                os.rename(newpath, oldpath)

        # if failed, roll back

    def execute(self):
        path = self.get_argument("path")
        self.protect(path)
        self.redirect("/fs/" + path)