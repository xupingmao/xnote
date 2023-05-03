# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/28 13:27:08
# @modified 2021/08/08 10:55:02

"""创建文件的选项背后的服务，包括创建文件、文件夹、插件等等"""

import os
import xauth
import xutils
import xconfig

PLUGIN_TEMPLATE      = xconfig.load_config_as_text("./config/plugin/plugin.tpl.py")
FORM_PLUGIN_TEMPLATE = xconfig.load_config_as_text("./config/plugin/form_plugin.tpl.py")

class BaseAddFileHandler:

    def handle_path(self, path):
        return path

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument_str("path", "")
        filename = xutils.get_argument_str("filename", "")
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

    def get_plugin_template(self):
        return PLUGIN_TEMPLATE

    def handle_path(self, path):
        if not path.endswith(".py"):
            return path + ".py"
        return path

    def create_file(self, path):
        user_name = xauth.current_name_str()
        code = self.get_plugin_template()
        code = code.replace("$since", xutils.format_datetime())
        code = code.replace("$author", user_name)
        code = code.replace("$date", xutils.format_date())
        xutils.writefile(path, code)

class AddFormPluginFileHandler(AddPluginFileHandler):

    def get_plugin_template(self):
        return FORM_PLUGIN_TEMPLATE


xurls = (
    r"/fs_api/add_dir", AddDirHandler,
    r"/fs_api/add_file", AddFileHandler,
    r"/fs_api/add_plugin", AddPluginFileHandler,
    r"/fs_api/add_form_plugin", AddFormPluginFileHandler,
)
