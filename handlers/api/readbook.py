# encoding=utf-8
# @author xupingmao
# @modified 2021/08/21 09:31:27
import os
import re
import xauth
import xutils
import json
from xutils import fsutil
from xutils import dbutil

dbutil.register_table("bookmark", "TXT书签")

def print_blue(msg):
    print("\033[34m\033[01m%s\033[0m" % msg, end = '')

def print_green(msg):
    print("\033[32m\033[01m%s\033[0m" % msg, end = '')

def debug_info(*msg):
    print_green("[DEBUG] ")
    print(*msg)

def seek_page(fp, bookmark, pagesize):
    # 缓存
    mod       = 20
    page      = bookmark.get("page", 0)
    startpage = 1

    if page < 0:
        page = 0
    fp.seek(0)

    startpage = int(page / mod) * mod
    pos = bookmark.get("page_%s" % startpage)
    if pos:
        debug_info("Hit cache, page=%s, position=%s" % (startpage, pos))
        fp.seek(pos)
    else:
        debug_info("No cache, startpage=0")
        startpage = 0
        fp.seek(0)

    for i in range(int(startpage), page):
        fp.read(pagesize)

    if page % mod == 0:
        bookmark["page_%s" % page] = fp.tell()


class handler:

    def safe_seek(self, fp, pos):
        for p in range(pos, pos-5, -1):
            if p <= 0:
                fp.seek(0)
                return
            try:
                fp.seek(p)
                cur = fp.tell()
                fp.read(1)
                fp.seek(cur)
                return
            except UnicodeDecodeError:
                xutils.print_exc()

    @xauth.login_required("admin")
    def GET(self):
        path      = xutils.get_argument("path")
        length    = 1000
        read      = xutils.get_argument("read", "false")
        direction = xutils.get_argument("direction", "forward")
        page      = 0

        if not path:
            return dict(code = "fail", message = "parameter path is empty")

        debug_info("path:", path)
        path = xutils.get_real_path(path)
        debug_info("real path:", path)

        if not os.path.exists(path):
            return dict(code = "fail", message = "file `%s` not exists" % path)

        basename, ext    = os.path.splitext(path)
        key              = "bookmark:%s:%s" % (xauth.current_name(), xutils.md5_hex(path))
        bookmark         = dbutil.get(key, {})
        bookmark['path'] = path
        page             = bookmark.get("page", 0)
        size             = xutils.get_file_size(path, format=False)
        debug_info("bookmark info:", bookmark)

        encoding = fsutil.detect_encoding(path)
        debug_info("detected encoding:", encoding)
        
        with open(path, encoding = encoding) as fp:
            text = "dummy"
            if direction == "backward":
                page = page - 1
            if direction == "forward":
                page = page + 1
            if page < 0:
                page = 0
            try:
                bookmark["page"] = page
                seek_page(fp, bookmark, length)
                current = fp.tell()
                text    = fp.read(length)
            except UnicodeDecodeError as e:
                # xutils.print_exc()
                bookmark['page'] = 0
                seek_page(fp, bookmark, length);
                current = fp.tell()
                text    = fp.read()

            if read == "true":
                xutils.say(text)

            if direction in ("forward", "backward"):
                # xutils.writefile(bookmarkpath, json.dumps(bookmark))
                dbutil.put(key, bookmark)
        return dict(code="success", data=text, page=page, current=current, size=size)

