from BaseHandler import *
from FileDB import FileService

searchable = False

class handler(BaseHandler):

    def default_request(self):
        name = self.get_argument("name")
        print(name)
        service = FileService.instance()
        return service.get_by_name(name)