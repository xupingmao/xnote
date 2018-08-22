# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2017
# @modified 2018/08/23 00:03:36
import os
import web
import xauth
import xconfig
import xutils
import xtemplate
import xmanager
from xutils import quote


def get_link(filename, webpath):
    if xutils.is_img_file(filename):
        return "![%s](%s)" % (filename, webpath)
    return "[%s](%s)" % (filename, webpath)

class UploadHandler:

    def POST(self):
        args = web.input(file = {}, dirname = None)
        x = args
        dirname = args.dirname
        if 'file' in x:
            if x.file.filename == "":
                raise web.seeother("//fs/%s" % quote(dirname))
            xutils.makedirs(dirname)
            filename = xutils.quote(os.path.basename(x.file.filename))
            filepath = os.path.join(dirname, filename)
            with open(filepath, "wb") as fout:
                # fout.write(x.file.file.read())
                for chunk in x.file.file:
                    fout.write(chunk)
            xmanager.fire("fs.upload", dict(path=filepath))
        raise web.seeother("/fs/%s" % quote(dirname))

    def GET(self):
        path, webpath = xutils.get_upload_file_path("")
        show_menu = (xutils.get_argument("show_menu") != "false")
        return xtemplate.render("fs/fs_upload.html", 
            show_menu = show_menu, 
            path = path)

class RangeUploadHandler:

    def merge_files(self, dirname, filename, chunks):
        dest_path = os.path.join(dirname, filename)
        with open(dest_path, "wb") as fp:
            for chunk in range(chunks):
                tmp_path = os.path.join(dirname, filename)
                tmp_path = "%s_%d.part" % (tmp_path, chunk)
                if not os.path.exists(tmp_path):
                    raise Exception("upload file broken")
                with open(tmp_path, "rb") as tmp_fp:
                    fp.write(tmp_fp.read())
                xutils.remove(tmp_path, True)
            xmanager.fire("fs.upload", dict(path=dest_path))


    @xauth.login_required()
    def POST(self):
        part_file = True
        chunksize = 5 * 1024 * 1024
        chunk = xutils.get_argument("chunk", 0, type=int)
        chunks = xutils.get_argument("chunks", 1, type=int)
        file = xutils.get_argument("file", {})
        prefix = xutils.get_argument("prefix", "")
        dirname = xutils.get_argument("dirname", xconfig.DATA_DIR)
        # Fix 安全问题，不能访问上级目录
        dirname = dirname.replace("$DATA", xconfig.DATA_DIR)
        filename = None
        webpath  = ""
        origin_name = ""

        if hasattr(file, "filename"):
            origin_name = file.filename
            xutils.log("recv {}", file.filename)
            filename = os.path.basename(file.filename)
            filename = xutils.get_real_path(filename)
            if dirname == "auto":
                filepath, webpath = xutils.get_upload_file_path(filename, replace_exists=True, prefix=prefix)
                dirname  = os.path.dirname(filepath)
                filename = os.path.basename(filepath)

            if part_file:
                tmp_name = "%s_%d.part" % (filename, chunk)
                seek = 0
            else:
                tmp_name = filename
                seek = chunk * chunksize
            tmp_path = os.path.join(dirname, tmp_name)

            with open(tmp_path, "wb") as fp:
                fp.seek(seek)
                if seek != 0:
                    xutils.log("seek to {}", seek)
                for file_chunk in file.file:
                    fp.write(file_chunk)
        else:
            return dict(code="fail", message="require file")
        if part_file and chunk+1==chunks:
            self.merge_files(dirname, filename, chunks)
        return dict(code="success", webpath=webpath, link=get_link(origin_name, webpath))

xurls = (
    # 和文件系统的/fs/冲突了
    r"/fs_upload", UploadHandler, 
    r"/fs_upload/range", RangeUploadHandler
)
