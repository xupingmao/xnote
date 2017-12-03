# encoding=utf-8
import os
import re
import xauth
import xutils
import json

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

    def seek_page(self, fp, bookmark, pagesize):
        # 缓存
        mod = 20
        page = bookmark.get("page", 1)
        # cache = bookmark.get("cache", {})
        startpage = 0

        if page < 0:
            page = 0
        fp.seek(0)

        startpage = int(page / mod) * mod
        pos = bookmark.get("page_%s"%startpage)
        if pos:
            print("Hit cache, page=%s, position=%s" % (startpage, pos))
            fp.seek(pos)
        else:
            startpage = 0

        for i in range(int(startpage), page-1):
            # cache[page] = fp.tell()
            fp.read(pagesize)
        if page % mod == 0:
            bookmark["page_%s" % page] = fp.tell()
        # bookmark["cache"] = cache

    @xauth.login_required("admin")
    def GET(self):
        path    = xutils.get_argument("path")
        length  = 1000
        read    = xutils.get_argument("read", "false")
        direction = xutils.get_argument("direction", "forward")
        page    = xutils.get_argument("page", 1, type=int)
        encoding = "utf-8"

        if not os.path.exists(path):
            path = xutils.quote_unicode(path)
        basename, ext = os.path.splitext(path)
        bookmarkpath = basename + ".bookmark"
        bookmark = dict()
        if os.path.exists(bookmarkpath):
            try:
                bookmark = json.loads(xutils.readfile(bookmarkpath))
                if not isinstance(bookmark, dict):
                    bookmark = dict()
            except:
                pass
        page = bookmark.get("page", 1)
        size = xutils.get_file_size(path, format=False)

        with open(path, encoding=encoding) as fp:
            text = "dummy"
            if direction == "backward":
                page = page - 1
            if direction == "forward":
                page = page + 1
            bookmark["page"] = page
            self.seek_page(fp, bookmark, length)
            current = fp.tell()
            text = fp.read(length)
            if read == "true":
                xutils.say(text)
            if direction in ("forward", "backward"):
                xutils.savetofile(bookmarkpath, json.dumps(bookmark))
        return dict(code="success", data=text, page=page, current=current, size=size)

