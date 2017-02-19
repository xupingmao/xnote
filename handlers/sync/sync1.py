from BaseHandler import *
from config import *
import os

def FileInfo(fname, st):
    if st is None:
        return dict(name=fname)
    return dict(name=fname, mtime=int(st.st_mtime*1000), size=st.st_size)

def get_dir_info(root):
    # save last sync info?
    info_list = []
    for fname in os.listdir(root):
        path = os.path.join(root, fname)
        try:
            st = os.stat(path)
            info_list.append(FileInfo(fname, st))
        except:
            info_list.append(FileInfo(fname, None))
    return info_list

def get_system_info():
    return get_dir_info(WORKING_DIR)

def get_modle_info():
    return get_dir_info(os.path.join(WORKING_DIR, "model"))

searchable = False

class handler(BaseHandler):

    def default_request(self):
        path = self.get_argument("path")
        filepath = os.path.join(WORKING_DIR, path)
        return fsutil.readbytes(filepath)

