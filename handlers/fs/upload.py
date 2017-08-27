# encoding=utf-8

import os
import web
import xauth
import xconfig
import xutils
from xutils import quote


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
        raise web.seeother("/fs/%s" % quote(dirname))

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
                xutils.remove(tmp_path)


    @xauth.login_required()
    def POST(self):
        # xutils.print_web_ctx_env()
        chunk = xutils.get_argument("chunk", 0, type=int)
        chunks = xutils.get_argument("chunks", 1, type=int)
        file = xutils.get_argument("file", {})
        dirname = xutils.get_argument("dirname", xconfig.DATA_DIR)
        dirname = dirname.replace("$DATA", xconfig.DATA_DIR)
        # print(file.__dict__)
        # print("%d/%d" % (chunk, chunks))
        filename = None
        if hasattr(file, "filename"):
            # print(" - - %-20s = %s" % ("filename", file.filename))
            xutils.log("recv {}", file.filename)
            filename = os.path.basename(file.filename)
            filename = xutils.quote_unicode(filename)
            # filename = xauth.get_current_name() + '_' + filename
            tmp_name = "%s_%d.part" % (filename, chunk)
            tmp_path = os.path.join(dirname, tmp_name)
            with open(tmp_path, "wb") as fp:
                for file_chunk in file.file:
                    fp.write(file_chunk)
        else:
            return dict(code="fail", message="require file")
        if chunk+1==chunks:
            self.merge_files(dirname, filename, chunks)
        return dict(code="success")

xurls = (
    # 和文件系统的/fs/冲突了
    r"/fs_upload", UploadHandler, 
    r"/fs_upload/range", RangeUploadHandler
)
