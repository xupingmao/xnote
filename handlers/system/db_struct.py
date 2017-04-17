from handlers.base import *
from handlers.file import dao

class handler(BaseHandler):

    def execute(self):
        table_struct = dao.get_table_struct("file")
        self.render("system/db_struct.html", table_struct = table_struct)