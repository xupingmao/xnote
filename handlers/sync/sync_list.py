from handlers.base import *
import config
import hashlib
from urllib.request import urlopen
from FileDB import *

WORKING_DIR = config.WORKING_DIR

_POSSIBLE_HOST = config.PARTNER_HOST_LIST

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

def is_same_file(fdata, path):
    if os.path.exists(path):
        st = os.stat(path)
        fdata.localsize = st.st_size
        if fdata.type == "file" and fdata.md5 != None:
            if fdata.size != st.st_size:
                return False
            md5 = hashlib.md5(fsutil.readbytes(path)).hexdigest()
            fdata.localmd5 = md5
            if md5 == fdata.md5:
                return True
            else:
                return False
    else:
        fdata.localsize = 0
    return False

def compute_diff(url, datalist):
    newdatalist = []
    for fdata in datalist:
        path = fdata.path
        if is_same_file(fdata, path):
            continue
        elif fdata.type == "dir":
            continue
        newdatalist.append(fdata)
        if fdata.type == 'dir':
            fdata['class'] = 'sync-dir'
            fdata.url = "/sync_list?url=%s&path=%s" % (url, fdata.path)
        elif fdata.size != fdata.localsize:
            fdata['class'] = 'sync-diff'
            fdata.url = "%s/sync?path=%s" % (url, fdata.path)
        else:
            fdata['class'] = 'sync-file'
            fdata.url = "%s/sync?path=%s" % (url, fdata.path)
    newdatalist.sort(key = lambda x : 0 if x['type'] == 'dir' else 1)
    return newdatalist
    # for fdata in datalist:

def compute_db_diff(diff_list):
    service = FileService.instance()
    new_list = []
    for file in diff_list:
        name = file.name
        db = service.get_by_name(name)
        if db is not None:
            if db.smtime == file.smtime:
                continue
            if db.content == file.content and db.related == file.related:
                continue
            file.localsmtime = db.smtime
            file.localmtime  = db.mtime
        else:
            file.localsmtime = dateutil.format_time(0)
            file.localmtime  = 0
        new_list.append(file)
    return new_list

def guess_url():
    for url in _POSSIBLE_HOST:
        if url == config.get("host"):
            continue
        full = netutil.get_http_home(url)
        try:
            value = urlopen(full+"/test", timeout = 0.5).read().decode("utf-8")
            if value == "success":
                return url
        except:
            pass
    return ""

def quote(text):
    return text.replace("+", "%2B")

class handler(BaseHandler):

    def default_request(self):
        url = self.get_argument("url", "")
        path = self.get_argument("path", "")
        days = self.get_argument("days", "7")
        diff = []

        if url == "":
            url = guess_url()

        if url != "" and url[-1] == '/':
            url = url[:-1]
        qurl = url

        if url != "":
            url = netutil.get_http_home(url)

        if path != "":
            qurl = url + "/sync_info?path=%s" % path
        else:
            qurl = url + "/sync_info"

        if url != "":
            data = get_json(qurl)
            diff = compute_diff(url, data)
        if url != "":
            db_diff_list = get_json(url + "/file_recent_modified?option=json&days=" + days)
            db_diff_list = compute_db_diff(db_diff_list)
        else:
            db_diff_list = []
        self.render("sync-list.html", diff_list = diff, 
            db_diff_list = db_diff_list, url = url,
            quote = quote)
        # return get_system_info()

name = "新xnote同步工具"
searchkey = "sync|同步"