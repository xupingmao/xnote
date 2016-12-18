from BaseHandler import *
from FileDB import FileService

class handler(BaseHandler):

    def execute(self):
        table_struct = FileService.instance().getTableDefine("file")
        self.render("system/db_struct.html", table_struct = table_struct)