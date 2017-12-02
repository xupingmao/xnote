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
        page = bookmark.get("page", 1)
        # cache = bookmark.get("cache", {})
        startpage = 0

        fp.seek(0)
        # if len(cache) > 0:
        #     startpage = sorted(cache.keys())[-1]
        #     print("find startpage %s,%s" % (startpage, cache[startpage]))
        #     fp.seek(cache[startpage])
        for i in range(int(startpage), page-1):
            # cache[page] = fp.tell()
            fp.read(pagesize)
        # bookmark["cache"] = cache

    @xauth.login_required("admin")
    def GET(self):
        path    = xutils.get_argument("path")
        length  = xutils.get_argument("length", 200, type=int)
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
        with open(path, encoding=encoding) as fp:
            text = "dummy"
            if direction == "backward":
                page = page - 1
            if direction == "forward":
                page = page + 1
            bookmark["page"] = page
            self.seek_page(fp, bookmark, length)
            text = fp.read(length)
            if read == "true":
                xutils.say(text)
            if direction in ("forward", "backward"):
                xutils.savetofile(bookmarkpath, json.dumps(bookmark))
        return dict(code="success", data=text, page=page)

