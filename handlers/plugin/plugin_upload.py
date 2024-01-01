# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-07-08 10:54:36
@LastEditors  : xupingmao
@LastEditTime : 2024-01-01 17:20:58
@FilePath     : /xnote/handlers/plugin/plugin_upload.py
@Description  : 描述
"""

import xutils
import re
import os
from xnote.core import xauth, xconfig
from xnote.plugin import PluginMetaKey

from .plugin_page import load_plugin_file
from xutils.webutil import SuccessResult, FailedResult

class PluginUploadHandler:

    pattern_str = r"[0-9a-zA-Z\-_]"
    pattern = re.compile(pattern_str)

    def check_plugin_id(self, plugin_id=""):
        if not self.pattern.match(plugin_id):
            return "plugin_id 必须满足%r规则" % self.pattern_str
        return None

    @xauth.login_required("admin")
    def POST(self):
        content = xutils.get_argument_str("content")
        meta = xutils.load_script_meta_by_code(content)
        plugin_id = meta.get_str_value(PluginMetaKey.id.value)
        if plugin_id == "" or plugin_id == None:
            return FailedResult(code="400", message="id 不能为空")
        err = self.check_plugin_id(plugin_id)
        if err != None:
            return FailedResult(code="400", message=err)
        
        xutils.makedirs(xconfig.FileConfig.plugins_upload_dir)
        plugin_path = os.path.join(xconfig.FileConfig.plugins_upload_dir, plugin_id + ".py")
        with open(plugin_path, "w+") as fp:
            fp.write(content)
        
        # 加载插件
        try:
            load_plugin_file(plugin_path, raise_exception=True)
            return SuccessResult()
        except Exception as e:
            return FailedResult(message=str(e))

xurls = (
    r"/plugins_upload", PluginUploadHandler,
)