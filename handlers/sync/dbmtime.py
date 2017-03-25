from handlers.base import *
import os

searchable = False

class handler(BaseHandler):
    """docstring for handler"""
    def execute(self):
        st = os.stat("data.db")
        return st.st_mtime