from handlers.base import *
from .dao import FileDO
from . import dao

class handler(BaseHandler):

    def execute(self):
        name = self.get_argument("name", "")
        tags = self.get_argument("tags", "")
        key  = self.get_argument("key", "")
        parent_id = self.get_argument("parent_id")

        file = FileDO(name)
        file.atime = dateutil.get_seconds()
        file.satime = dateutil.format_time()
        file.mtime = dateutil.get_seconds()
        file.smtime = dateutil.format_time()
        file.ctime = dateutil.get_seconds()
        file.sctime = dateutil.format_time()
        file.parent_id = int(parent_id)
        error = ""
        try:
            if name != '':
                dao.insert(file)
                record = dao.get_by_name(name)
                raise web.seeother("/file/edit?id=%s" % record.id)
        except Exception as e:
            error = e
        self.render(key = "", name = key, tags = tags, error=error)