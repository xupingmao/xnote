from handlers.base import *
from . import dao

class handler(BaseHandler):

    def execute(self):
        id = int(self.get_argument("id"))
        name = self.get_argument("name", "")
        parent_id = self.get_argument("parent_id", -1)

        record = dao.get_by_id(id)

        if parent_id > 0:
            dao.update(where = "id=%s" % id, parent_id = parent_id)
            raise web.seeother("/file/edit?id=%s" % id)

        if name != "" and name != None:
            filelist = dao.search_name(name)
            newlist = []
            for f in filelist:
                if f.id == id:
                    continue
                else:
                    newlist.append(f)
            filelist = newlist
        else:
            filelist = []
        self.render("file/archive.html", record = record, filelist = filelist)