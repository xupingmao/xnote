from BaseHandler import *
from config import *
from urllib.request import urlopen
import hashlib

BLACK_LIST = ["__pycache__", "static", "tests"]

EXT_BLACK_LIST = [".log"]

MAX_FILE_SIZE = 10 * 1024 ** 2; # 10 Mb

def FileInfo(path, st):
    path = path.replace("\\", "/")
    md5 = None
    if os.path.isdir(path):
        type = "dir"
    elif os.path.isfile(path):
        type = "file"
        bytes = fsutil.readbytes(path)
        md5 = hashlib.md5(bytes).hexdigest()
    else:
        type = None
    if st is None:
        return dict(path=path, type = type, md5 = None)
    return dict(path=path, type = type, 
        mtime=int(st.st_mtime*1000), 
        size=st.st_size,
        md5 = md5)

def checkfilename(fname):
    if fname in BLACK_LIST:
        return False
    name, ext = os.path.splitext(fname)
    if ext in EXT_BLACK_LIST:
        return False
    return True

def get_file_info(path, info_list):
    try:
        st = os.stat(path)
        if st.st_size > MAX_FILE_SIZE:
            return
        info_list.append(FileInfo(path, st))
    except:
        info_list.append(FileInfo(path, None))

def get_dir_info(root, info_list = None):
    # default value is a global value, which will keep increase
    if info_list is None:
        info_list = []
    # save last sync info?
    for fname in os.listdir(root):
        path = os.path.join(root, fname)
        if not checkfilename(fname):
            continue

        if os.path.isdir(path):
            get_dir_info(path, info_list)
        get_file_info(path, info_list)

    return info_list

def get_dirs_info(dir_list):
    info_list = []
    for dirname in dir_list:
        get_dir_info(dirname, info_list)
    return info_list

def get_system_info():
    # home directory
    return get_dirs_info(["./", "./static/css"])

def get_modle_info():
    return get_dir_info(os.path.join(WORKING_DIR, "model"))

def get_json(url):
    content = urlopen(url).read()
    return json.loads(content)

def compute_diff(datalist):
    return datalist
    # for fdata in datalist:

searchable = False

class handler(BaseHandler):

    def default_request(self):
        path = self.get_argument("path", "")
        if path != "":
            return get_dir_info(path)
        return get_system_info()
        