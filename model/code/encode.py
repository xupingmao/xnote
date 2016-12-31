# coding=utf-8

import web
import os
import base64
import json
import time
import xutils
import web.xtemplate as xtemplate

class FileItem(object):
    """docstring for FileItem"""
    def __init__(self, filepath):
        super(FileItem, self).__init__()
        self.path = filepath
        self.name = os.path.basename(filepath)
        if os.path.isfile(filepath):
            self.type = "file"
        elif os.path.isdir(filepath):
            self.type = "dir"
        else:
            self.type = "symbol"

    def __lt__(self, other):
        """Python的sort和C++一样重写小于号即可"""
        if self.type != other.type and self.type == "dir":
            return True
        elif self.type != other.type and other.type == "dir":
            return False
        return self.name < other.name


def getfilelist(path):
    filelist = []
    for name in os.listdir(path):
        filepath = os.path.join(path, name)
        file = FileItem(filepath)
        filelist.append(file)
    return sorted(filelist)

class handler:

    def GET(self):
        args = web.input(password="")
        path = args.path
        password = args.password

        filelist = getfilelist(path)

        return xtemplate.render("code/encode.html",
            path = path,
            password = password,
            filelist = filelist)

    def encode_filelist(self, path):
        filelist = getfilelist(path)

        namefile = os.path.join(path, "xnote-index.json")

        if os.path.exists(namefile):
            # 防止重复加密导致信息丢失
            bakname = "xnote-index-%s.json" % time.time()
            os.rename(namefile, os.path.join(path, bakname))

        rename_dict = {}
        for index, file in enumerate(filelist):
            newname = "%03d" % index
            if file.name.endswith(".json"):
                continue
            newpath = os.path.join(path, newname)
            os.rename(file.path, newpath)
            rename_dict[newname] = base64.b64encode(file.name.encode("utf-8")).decode("utf-8")
        text = json.dumps(rename_dict)
        namefile = os.path.join(path, "xnote-index.json")
        xutils.savetofile(namefile, text)

    def decode_filelist(self, path):
        namefile = os.path.join(path, "xnote-index.json")
        text = xutils.readfile(namefile)
        rename_dict = json.loads(text)

        filelist = getfilelist(path)
        for index, file in enumerate(filelist):
            if file.name.endswith(".json"):
                continue
            newname = rename_dict[file.name]
            newname = base64.b64decode(newname.encode("utf-8")).decode("utf-8")
            newpath = os.path.join(path, newname)
            os.rename(file.path, newpath)


    def POST(self):
        args = web.input(password="")
        path = args.path
        password = args.password
        type = args.type

        if type == "encode":
            self.encode_filelist(path)
        elif type == "decode":
            self.decode_filelist(path)

        filelist = getfilelist(path)
        return xtemplate.render("code/encode.html",
            path = path,
            password = password,
            filelist = filelist)