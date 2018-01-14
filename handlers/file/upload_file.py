# encoding=utf-8
import os
import time
import xutils
import xtemplate

def get_link(filename, webpath):
    if xutils.is_img_file(filename):
        return "![%s](%s)" % (filename, webpath)
    return "[%s](%s)" % (filename, webpath)

class handler:

    def POST(self):
        file = xutils.get_argument("file", {})
        type = xutils.get_argument("type", "normal")
        prefix = xutils.get_argument("prefix", "")
        filepath = ""
        filename = ""
        if not hasattr(file, "filename") or file.filename == "":
            return xtemplate.render("file/upload_file.html", filepath = filepath, filename = filename)
        filename = file.filename
        # Fix IE HMTL5 API拿到了全路径
        filename = os.path.basename(filename)
        filepath, webpath = xutils.get_upload_file_path(filename, prefix=prefix)
        with open(filepath, "wb") as fout:
            # fout.write(x.file.file.read())
            for chunk in file.file:
                fout.write(chunk)

        if type == "html5":
            return dict(success=True, message="上传成功", link=get_link(filename, webpath))
        return xtemplate.render("file/upload_file.html", 
            filepath = webpath, 
            filename = filename, 
            is_img=is_img(filename))

    def GET(self):
        return self.POST()


        