# coding=utf-8

import web
import os
import base64
import json
import time
import xutils
import xtemplate

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
        # namefile = os.path.join(path, "xnote-index.json")

        # if os.path.exists(namefile):
            # 防止重复加密导致信息丢失
            # bakname = "xnote-index-%s.json" % time.strftime("%Y_%m_%d_%H_%M_%S")
            # os.rename(namefile, os.path.join(path, bakname))

        rename_dict = {}
        for index, file in enumerate(filelist):
            if file.type == "dir":
                continue
            if file.name.endswith(".xenc"):
                continue
            newname = base64.urlsafe_b64encode(file.name.encode("utf-8")).decode("utf-8") + ".xenc"
            newpath = os.path.join(path, newname)
            os.rename(file.path, newpath)
        #     if file.name.endswith(".json"):
        #         continue
        #     newpath = os.path.join(path, newname)
        #     os.rename(file.path, newpath)
        #     rename_dict[newname] = base64.b64encode(file.name.encode("utf-8")).decode("utf-8")
        # text = json.dumps(rename_dict)
        # namefile = os.path.join(path, "xnote-index.json")
        # xutils.savetofile(namefile, text)

    def decode_filelist(self, path):
        # namefile = os.path.join(path, "xnote-index.json")
        # text = xutils.readfile(namefile)
        # rename_dict = json.loads(text)
        # for key in rename_dict:
        #     newname = rename_dict[key]
        #     newname = base64.b64decode(newname.encode("utf-8")).decode("utf-8")
        #     print(newname)
        errors = []
        filelist = getfilelist(path)
        for index, file in enumerate(filelist):
            if file.type == "dir":
                continue
            if not file.name.endswith(".xenc"):
                continue
            name = file.name[:-5]
            newname = base64.urlsafe_b64decode(name.encode("utf-8")).decode("utf-8")
            # print(newname)
            newpath = os.path.join(path, newname)
            try:
                os.rename(file.path, newpath)
            except Exception as e:
                errors.append(str(e))
        if len(errors) > 0:
            raise Exception(errors)


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