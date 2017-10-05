# encoding=utf-8
import web
import xtemplate
import xutils

from . import dao

class handler:

    def GET(self):
        id = int(xutils.get_argument("id"))
        name = xutils.get_argument("name", "")
        parent_id = xutils.get_argument("parent_id", "")
        record = dao.get_by_id(id)
        if parent_id != "":
            dao.update(where=dict(id=id), parent_id = parent_id)
            raise web.seeother("/file/view?id=%s" % id)

        if name != "" and name != None:
            filelist = dao.search_name(name, file_type="group")
            newlist = []
            for f in filelist:
                if f.id == id:
                    continue
                else:
                    newlist.append(f)
            filelist = newlist
        else:
            filelist = []
        return xtemplate.render("file/archive.html", record = record, filelist = filelist)