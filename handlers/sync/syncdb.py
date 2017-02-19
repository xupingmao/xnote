from BaseHandler import *
from FileDB import FileService
from web.db import SqliteDB

searchable = False

_POSSIBLE_HOST = config.PARTNER_HOST_LIST

def guess_url():
    for url in _POSSIBLE_HOST:
        if url == config.get("host"):
            continue
        full = netutil.get_http_home(url)
        try:
            value = urlopen(full+"/test", timeout = 0.5).read().decode("utf-8")
            if value == "success":
                return netutil.get_http_url(url)
        except:
            pass
    return ""

def read_http_file(url, mode="r"):
    bytes = urlopen(url).read()
    if mode == "rb":
        return bytes
    else:
        return bytes.decode("utf-8")

def get_remote_dbmtime(host):
    content = read_http_file(host+"/sync/dbmtime")
    return float(content)

def backup_data():
    date = dateutil.get_date()
    filename = "backup/data." + date + ".db"
    fsutil.check_create_dirs("backup")

    with open("data.db", "rb") as f:
        open(filename, "wb").write(f.read())


class handler(BaseHandler):

    def execute(self):
        url = self.get_argument("url", "")
        error = ""
        if url == "":
            url = guess_url()
        if web.ctx.method == "POST" and url != "":
            remote_dbmtime = get_remote_dbmtime(url)
            local_dbmtime  = os.stat("data.db").st_mtime
            if local_dbmtime < remote_dbmtime:
                backup_data()
                open("data.db", "wb").write(read_http_file(url+"/system/download_db", "rb"))
                error = "sync db done!"
            else:
                error = "local_dbmtime(%s) > remote_dbmtime(%s)" % (local_dbmtime, remote_dbmtime)
        self.render("sync/syncdb.html", url = url, error = error)

    def old(self):
        name   = self.get_argument("name")
        url    = self.get_argument("url")
        print(name)
        # name   = name.replace("+", "%2B");
        # qname = quote(name)
        fullurl = url + "/file_json?name=%s" % quote(name)
        obj = get_json(fullurl)
        # obj = get_json(url + "/file_json?name=%s" % name)
        # print(obj)
        # return obj
        # service = FileService.instance()
        # record = service.select(name=name)

        db = SqliteDB(db="data.db")
        record = db.select("file", where="name='%s'" % name)
        print(record)
        # for r in record:
        #     print(r)
        first = record.first()
        print(first)
        if first is None:
            del obj.id
            db.insert("file", **obj)
        else:
            del obj.id
            del obj.name
            db.update("file", where="name='%s'" % name, **obj)
        return "success"