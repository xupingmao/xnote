# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-07-08 10:54:36
@LastEditors  : xupingmao
@LastEditTime : 2023-07-08 11:26:47
@FilePath     : /xnote/handlers/plugin/plugin_upload.py
@Description  : 描述
"""

import xauth
import xutils
import re
import xconfig
import os

from .plugin import load_plugin_file
from xutils.webutil import SuccessResult, FailedResult

class PluginUploadHandler:

    pattern_str = r"[0-9a-zA-Z\-_]"
    pattern = re.compile(pattern_str)

    def check_namespace(self, namespace=""):
        if not self.pattern.match(namespace):
            return "namespace必须满足%r规则" % self.pattern_str
        return None

    xauth.login_required("admin")
    def POST(self):
        content = xutils.get_argument_str("content")
        meta = xutils.load_script_meta_by_code(content)
        namespace = meta.get_str_value("namespace")
        if namespace == "" or namespace == None:
            return FailedResult(code="400", message="namespace不能为空")
        err = self.check_namespace(namespace)
        if err != None:
            return FailedResult(code="400", message=err)
        
        xutils.makedirs(xconfig.FileConfig.plugins_upload_dir)
        plugin_path = os.path.join(xconfig.FileConfig.plugins_upload_dir, namespace + ".py")
        with open(plugin_path, "w+") as fp:
            fp.write(content)
        
        # 加载插件
        load_plugin_file(plugin_path)
        return SuccessResult()


xurls = (
    r"/plugins_upload", PluginUploadHandler,
)