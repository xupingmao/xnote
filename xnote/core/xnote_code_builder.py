# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/19 12:45:23
# @modified 2022/04/09 18:43:28
# @filename build.py

import os
import shutil
import threading
import typing
from typing import List, BinaryIO
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
    
    def append_file_to(self, fpath, target_fp: typing.BinaryIO):
        with open(fpath, "rb") as read_fp:
            self._do_append_file(read_fp, target_fp)
    
    def _do_append_file(self, read_fp: BinaryIO, target_fp: BinaryIO):
        def _write_line(line: bytes):
            line = line.strip()
            target_fp.write(line)
            target_fp.write(b"\n")
        
        is_in_comment_block = False
        for line in read_fp.readlines():
            if is_in_comment_block:
                comment_end = line.find(b"*/")
                if comment_end >= 0:
                    is_in_comment_block = False
                    # 写入注释后面内容
                    _write_line(line[comment_end+2:])
                else:
                    pass # still in comment block
            else:
                line = line.strip()
                if len(line) == 0:
                    continue
                
                if line.startswith(b"//"):
                    # 快速判断,不准确
                    continue
                
                p1 = line.find(b"//")
                if p1 >= 0:
                    # 行尾注释
                    target_fp.write(line[:p1].strip())
                    target_fp.write(b"\n")
                    continue
                
                comment_start = line.find(b"/*")
                if comment_start >= 0:
                    # 写入注释前面内容
                    target_fp.write(line[:comment_start].strip())
                    comment_end = line.find(b"*/", comment_start)
                    if comment_end >= 0:
                        # 同一行注释
                        _write_line(line[comment_end+2:])
                    else:
                        # 多行注释
                        is_in_comment_block = True
                    continue

                _write_line(line)
    
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
    with FileBuilder("./_static/css/app.build.css") as builder:
        builder.append("./_static/lib/font-awesome-4.7.0/css/font-awesome.min.css")

        # 通用的css
        builder.append("./_static/css/base/reset.css")
        builder.append("./_static/css/base/common.css")
        builder.append("./_static/css/base/common-span.css")
        builder.append("./_static/css/base/common-link.css")
        builder.append("./_static/css/base/common-list.css")
        builder.append("./_static/css/base/common-mobile.css")
        builder.append("./_static/css/base/common-icon.css")
        builder.append("./_static/css/base/common-tag.css")
        builder.append("./_static/css/base/common-layout.css")
        builder.append("./_static/css/base/common-button.css")
        builder.append("./_static/css/base/common-markdown.css")
        builder.append("./_static/css/base/common-dialog.css")
        builder.append("./_static/css/base/common-tab.css")
        builder.append("./_static/css/base/common-dropdown.css")
        builder.append("./_static/css/base/common-page.css")
        builder.append("./_static/css/base/common-photo.css")
        builder.append("./_static/css/base/common-form.css")
        builder.append("./_static/css/base/common-table.css")
        builder.append("./_static/css/base/common-tree.css")
        builder.append("./_static/css/base/common-select.css")
        builder.append("./_static/css/base/common-grid.css")
        builder.append("./_static/css/base/common-misc.css")

        # 场景化的css
        builder.append("./_static/css/common-react.css")
        builder.append("./_static/css/app.css")
        builder.append("./_static/css/message.css")
        builder.append("./_static/css/note.css")
        builder.append("./_static/css/note-comment.css")
        builder.append("./_static/css/plugins.css")
        builder.append("./_static/css/search.css")
        builder.append("./_static/css/todo.css")
        # echo "打包app.build.css ... [OK]"

        # 针对特殊设备的适配
        builder.append("./_static/css/base/reset-wide.css")

def build_utils_js():
    with FileBuilder("./_static/js/utils.build.js") as builder:
        # utils.js
        builder.append("./_static/js/base/array.js")
        builder.append("./_static/js/base/string.js")
        builder.append("./_static/js/base/datetime.js")
        builder.append("./_static/js/base/misc.js")
        builder.append("./_static/js/base/jq-ext.js")

def build_app_js():
    with FileBuilder("./_static/js/app.build.js") as builder:
        # utils.build.js 也都合并到 app.build.js 文件中
        builder.append("./_static/js/utils.build.js")

        # xnote-ui
        builder.append("./_static/js/xnote-ui/x-init.js")
        builder.append("./_static/js/xnote-ui/x-event.js")
        builder.append("./_static/js/xnote-ui/x-ext.js")
        builder.append("./_static/js/xnote-ui/x-core.js")
        builder.append("./_static/js/xnote-ui/layer.photos.js")
        builder.append("./_static/js/xnote-ui/x-device.js")
        builder.append("./_static/js/xnote-ui/x-dropdown.js")
        builder.append("./_static/js/xnote-ui/x-photo.js")
        builder.append("./_static/js/xnote-ui/x-audio.js")
        builder.append("./_static/js/xnote-ui/x-upload.js")
        builder.append("./_static/js/xnote-ui/x-dialog.js")
        builder.append("./_static/js/xnote-ui/x-tab.js")
        builder.append("./_static/js/xnote-ui/x-layout.js")
        builder.append("./_static/js/xnote-ui/x-template.js")
        builder.append("./_static/js/xnote-ui/x-url.js")
        builder.append("./_static/js/xnote-ui/x-table.js")

        # app.js
        builder.append("./_static/js/app.js")
        builder.append("./_static/js/note.js")
        builder.append("./_static/js/note-comment.js")
        builder.append("./_static/js/editor.js")
        builder.append("./_static/js/fs/fs.js")

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
