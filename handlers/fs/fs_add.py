# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/28 13:27:08
# @modified 2020/01/29 23:55:37
import os
import xauth
import xutils
import xconfig
from xutils import fsutil

class BaseAddFileHandler:

    def handle_path(self, path):
        return path

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path", "")
        filename = xutils.get_argument("filename", "")
        if path == "":
            return dict(code="fail", message="path is empty")
        if xconfig.USE_URLENCODE:
            filename = xutils.quote_unicode(filename)
        newpath = os.path.join(path, filename)
        
        # 有些需要补全后缀等操作
        newpath = self.handle_path(newpath)

        if os.path.exists(newpath):
            if os.path.isdir(newpath):
                return dict(code = "fail", message = "文件夹[%s]已经存在" % filename)
            return dict(code = "fail", message = "文件[%s]已经存在" % filename)

        try:
            self.create_file(newpath)
            return dict(code="success")
        except Exception as e:
            xutils.print_exc()
            return dict(code="fail", message=str(e))

    def create_file(self, path):
        raise NotImplementedError()

class AddDirHandler(BaseAddFileHandler):

    def create_file(self, path):
        os.makedirs(path)

class AddFileHandler(BaseAddFileHandler):

    def create_file(self, path):
        xutils.touch(path)

class AddPluginFileHandler(BaseAddFileHandler):

    def handle_path(self, path):
        if not path.endswith(".py"):
            return path + ".py"
        return path

    def create_file(self, path):
        user_name = xauth.current_name()
        code = xconfig.PLUGIN_TEMPLATE
        code = code.replace("$since", xutils.format_datetime())
        code = code.replace("$author", user_name)
        xutils.writefile(path, code)

xurls = (
    r"/fs_api/add_dir", AddDirHandler,
    r"/fs_api/add_file", AddFileHandler,
    r"/fs_api/add_plugin", AddPluginFileHandler
)
