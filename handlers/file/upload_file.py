import time
from BaseHandler import *

class handler(BaseHandler):

    def create_file_name(self, filename):
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
        if x is not None and "file" in x:
            if not hasattr(x.file, "filename") or x.file.filename == "":
                self.render("file/upload_file.html", filepath = filepath, filename = filename)
                return
            filename = x.file.filename
            filepath = self.create_file_name(x.file.filename)
            fout = open(filepath, "wb")
            # fout.write(x.file.file.read())
            for chunk in x.file.file:
                fout.write(chunk)
            fout.close()
        self.render("file/upload_file.html", filepath = filepath, filename = filename)