from BaseHandler import *
import FileDB

class handler(BaseHandler):

    def execute(self):
        self.id = 0
        self.render(
            recentlist=FileDB.get_recent_visit(7), 
            category=FileDB.get_category(),
            )

searchable = False