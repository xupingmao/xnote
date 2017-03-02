# encoding=utf-8
import time
from BaseHandler import *

class handler(BaseHandler):

    def create_file_name(self, filename):
        # TODO 使用锁 threading.Lock
        # 可以使用with语句或者注解来简化
        date = dateutil.format_date(fmt="%Y/%m")
        origin_filename = "static/img/" + date + "/" + filename
        fsutil.check_create_dirs("static/img/"+date)
        fileindex = 1
        newfilename = origin_filename
        while os.path.exists(newfilename):
            name, ext = os.path.splitext(origin_filename)
            newfilename = name + str(fileindex) + ext
            fileindex+=1
        return newfilename

    def execute(self):
        x = web.input(file = {})
        filepath = ""
        filename = ""
        file = x.file

        if not hasattr(file, "filename") or file.filename == "":
            self.render("file/upload_file.html", filepath = filepath, filename = filename)
            return
        filename = file.filename
        filepath = self.create_file_name(file.filename)
        with open(filepath, "wb") as fout:
            # fout.write(x.file.file.read())
            for chunk in file.file:
                fout.write(chunk)
        self.render("file/upload_file.html", filepath = filepath, filename = filename)