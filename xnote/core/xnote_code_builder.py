# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/19 12:45:23
# @modified 2022/04/09 18:43:28
# @filename build.py

import os
import shutil
import threading
from . import xconfig

try:
    import termcolor
except ImportError:
    class termcolor:

        @staticmethod
        def colored(text, color):
            return text

BLOCKSIZE = 4 * 1024 # 4K
_lock = threading.RLock()

def green_text(text):
    return termcolor.colored(text, "green")

def red_text(text):
    return termcolor.colored(text, "red")

class FileBuilder:

    def __init__(self, fpath):
        self.target_path = xconfig.resolve_config_path(fpath)
        self.source_path_list = []

    def close(self):
        pass

    def append(self, fpath):
        fpath = xconfig.resolve_config_path(fpath)
        self.source_path_list.append(fpath)

    def __enter__(self):
        return self
    
    def append_file_to(self, fpath, target_fp):
        with open(fpath, "rb") as read_fp:
            shutil.copyfileobj(read_fp, target_fp, BLOCKSIZE)
    
    def do_build(self):
        with open(self.target_path, "wb+") as fp:
            for fpath in self.source_path_list:
                self.append_file_to(fpath, fp)
        
        print("文件构建完成:%s" % self.target_path)

    def __exit__(self, type, value, traceback):
        if not os.path.exists(self.target_path):
            self.do_build()
            return
        
        target_mtime = os.stat(self.target_path).st_mtime
        for fpath in self.source_path_list:
            source_mtime = os.stat(fpath).st_mtime
            if source_mtime > target_mtime:
                print("文件发生了修改:%s" % fpath)
                self.do_build()
                return

def build_app_css():
    with FileBuilder("./static/css/app.build.css") as builder:
        builder.append("./static/lib/font-awesome-4.7.0/css/font-awesome.min.css")

        # 通用的css
        builder.append("./static/css/base/reset.css")
        builder.append("./static/css/base/common.css")
        builder.append("./static/css/base/common-mobile.css")
        builder.append("./static/css/base/common-icon.css")
        builder.append("./static/css/base/common-tag.css")
        builder.append("./static/css/base/common-layout.css")
        builder.append("./static/css/base/common-button.css")
        builder.append("./static/css/base/common-markdown.css")
        builder.append("./static/css/base/common-dialog.css")
        builder.append("./static/css/base/common-tab.css")
        builder.append("./static/css/base/common-dropdown.css")
        builder.append("./static/css/base/common-page.css")
        builder.append("./static/css/base/common-photo.css")

        # 场景化的css
        builder.append("./static/css/common-react.css")
        builder.append("./static/css/app.css")
        builder.append("./static/css/message.css")
        builder.append("./static/css/note.css")
        builder.append("./static/css/plugins.css")
        builder.append("./static/css/search.css")
        builder.append("./static/css/todo.css")
        # echo "打包app.build.css ... [OK]"

        # 针对特殊设备的适配
        builder.append("./static/css/base/reset-wide.css")

def build_utils_js():
    with FileBuilder("./static/js/utils.build.js") as builder:
        # utils.js
        builder.append("./static/js/base/array.js")
        builder.append("./static/js/base/string.js")
        builder.append("./static/js/base/datetime.js")
        builder.append("./static/js/base/misc.js")
        builder.append("./static/js/base/jq-ext.js")

def build_app_js():
    with FileBuilder("./static/js/app.build.js") as builder:
        # utils.build.js 也都合并到 app.build.js 文件中
        builder.append("./static/js/utils.build.js")

        # xnote-ui
        builder.append("./static/js/xnote-ui/x-init.js")
        builder.append("./static/js/xnote-ui/x-event.js")
        builder.append("./static/js/xnote-ui/x-ext.js")
        builder.append("./static/js/xnote-ui/x-core.js")
        builder.append("./static/js/xnote-ui/layer.photos.js")
        builder.append("./static/js/xnote-ui/x-device.js")
        builder.append("./static/js/xnote-ui/x-dropdown.js")
        builder.append("./static/js/xnote-ui/x-photo.js")
        builder.append("./static/js/xnote-ui/x-audio.js")
        builder.append("./static/js/xnote-ui/x-upload.js")
        builder.append("./static/js/xnote-ui/x-dialog.js")
        builder.append("./static/js/xnote-ui/x-tab.js")
        builder.append("./static/js/xnote-ui/x-layout.js")
        builder.append("./static/js/xnote-ui/x-template.js")
        builder.append("./static/js/xnote-ui/x-url.js")

        # app.js
        builder.append("./static/js/app.js")
        builder.append("./static/js/note.js")
        builder.append("./static/js/fs/fs.js")

def build():
    with _lock:
        build_app_css()
        build_utils_js()
        build_app_js()

def main():
    with _lock:
        build_app_css()
        print("-"*50)

        build_utils_js()
        print("-"*50)

        build_app_js()
        print("-"*50)

        print(green_text("全部打包完成!"))

if __name__ == '__main__':
    main()
