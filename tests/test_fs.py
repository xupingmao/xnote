# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/11/29 14:45:21
# @modified 2022/06/03 14:33:36
import xutils
from .a import *
import os
import io
from contextlib import contextmanager
from unittest import mock
from xnote.core import xconfig
from xnote.core import xauth
from xutils import textutil, jsonutil, fsutil
from zipfile import ZipFile
from .test_base import json_request, BaseTestCase, request_html, json_request_return_dict
from .test_base import init as init_app, get_test_file_path, get_test_app
from xnote_handlers.fs.fs_index import build_fs_index
from xnote_handlers.fs.fs_helper import FileInfoDao, FileInfo

init_app()


class TestMain(BaseTestCase):

    def prepare_test_file(self, fname="", content=""):
        fpath = get_test_file_path(fname)
        with open(fpath, "w+") as fp:
            fp.write(content)
        return fpath

    @contextmanager
    def mock_file(self, fpath, data):
        """用内存数据 fake 掉指定路径的 open/os.stat/路径判断，避免大文件落盘。

        这样大文件下载/Range 的回归测试可以默认运行，而不会在磁盘上写入数十 MB 的数据。
        """
        real_os_stat = os.stat
        real_isdir = os.path.isdir
        fake_stat = mock.Mock()
        fake_stat.st_size = len(data)
        fake_stat.st_mtime = 0.0

        def stat_side(p, *args, **kw):
            if p == fpath:
                return fake_stat
            return real_os_stat(p, *args, **kw)

        orig_open = open
        def open_side(p, *args, **kw):
            if p == fpath:
                return io.BytesIO(data)
            return orig_open(p, *args, **kw)

        with mock.patch("os.stat", side_effect=stat_side), \
             mock.patch("os.path.isfile", side_effect=lambda p: p == fpath), \
             mock.patch("os.path.isdir", side_effect=lambda p: False if p == fpath else real_isdir(p)), \
             mock.patch("builtins.open", side_effect=open_side):
            yield

    def test_fs_view_mode(self):
        cwd = os.getcwd()

        self.check_OK(f"/fs/~{cwd}")
        self.check_OK(f"/fs/~{cwd}?mode=grid")
        self.check_OK(f"/fs/~{cwd}?mode=sidebar")

    def test_fs_hex(self):
        self.check_OK("/fs_hex")
        self.check_OK("/fs_hex?path=./README.md")

    def test_code_edit(self):
        self.check_OK("/code/edit?path=./README.md")
    
    def test_code_edit_part(self):
        old_config = xconfig.MAX_TEXT_SIZE
        xconfig.MAX_TEXT_SIZE = 100
        self.check_OK("/code/edit?path=./README.md")
        xconfig.MAX_TEXT_SIZE = old_config

    def test_code_edit_config(self):
        self.check_OK("/code/edit/config?config_key=config.init.script")
        data = dict(config_key = "config.init.script", content = "# init script")
        result = json_request_return_dict("/code/edit/config", method="POST", data = data)
        assert result["success"] == True

    def test_fs_tools(self):
        self.check_OK("/fs_tools")
        self.check_OK("/fs_bookmark")

    def test_create_file(self):
        path = xconfig.DATA_DIR
        resp = json_request_return_dict("/fs_api/add_file", method="POST",
                            data=dict(path=path, filename="test_fs.txt"))
        print(resp)
        self.assertEqual("success", resp["code"])

    def test_create_dir(self):
        path = xconfig.DATA_DIR
        resp = json_request_return_dict(
            "/fs_api/add_dir", 
            method="POST",
            data=dict(path=path, filename="test_fs_dir"))
        print(resp)
        self.assertEqual("success", resp["code"])
    
    def test_code_preview(self):
        self.check_OK("/code/preview?path=./README.md")

    def test_build_fs_index(self):
        size = build_fs_index(xconfig.DATA_DIR, sync=True)
        self.assertTrue(size > 0)

        dao = FileInfoDao()
        info = FileInfo()
        info.fpath = "/data/xxx"
        id1 = dao.save_by_fpath(info)
        id2 = dao.save_by_fpath(info)
        assert id1 == id2
    
    def test_fs_index_manage_page(self):
        path = xutils.quote("./testdata")
        self.check_OK("/fs_index?action=reindex&path={path}".format(path=path), method="POST")
        self.check_OK("/fs_index?p=rebuild")
        self.check_OK("/fs_index")

    def test_config_fs_order(self):
        resp = json_request_return_dict("/fs_api/config", method = "POST", data = dict(action = "sort", order = "size"))
        print(resp)
        self.assertEqual("success", resp["code"])
        
        user_id = xauth.current_user_id()
        self.assertEqual("size", xauth.get_user_config(user_id, "fs_order"))
    
    def test_fs_config_error(self):
        resp = json_request_return_dict("/fs_api/config", method = "POST", data = dict(action = "notfount", order = "size"))
        print(resp)
        self.assertEqual("error", resp["code"])
    
    def test_fs_sidebar(self):
        path = os.getcwd()
        txt_path = get_test_file_path("./fs_preview_test.txt")
        with open(txt_path, "w+") as fp:
            fp.write("test fs preview")

        self.check_OK("/fs_sidebar?path={path}".format(path=path))
        self.check_OK("/fs_preview?path={txt_path}".format(txt_path=txt_path))
        self.check_OK(f"/fs_preview?path={xutils.encode_base64(txt_path)}&b64=true")

        img_resp = request_html(f"/fs_preview?path=test.png")
        assert b"<img" in img_resp

    def test_fs_find(self):
        self.check_OK("/fs_find?key=test")
    
    def test_fs_find_in_cache(self):
        xconfig.USE_CACHE_SEARCH = True
        self.check_OK("/fs_find?key=test")

    def test_fs_upload_search(self):
        self.check_OK("/fs_upload/search?key=" + xutils.quote("test"))

    def test_fs_text(self):
        txt_path = get_test_file_path("./fs_preview_test.txt")
        with open(txt_path, "w+") as fp:
            fp.write("test fs preview")
        self.check_OK(f"/fs_text?method=contents&path={xutils.quote(txt_path)}")
        self.check_OK(f"/fs_text?method=readpage&path={xutils.quote(txt_path)}")
        self.check_OK(f"/fs_text?method=refresh&path={xutils.quote(txt_path)}")

    def test_fs_download(self):
        from xnote_handlers.system.system_sync.dao import SystemSyncTokenDao, SystemSyncToken
        fpath = self.prepare_test_file("./test_download.txt", "test download")
        fpath_b64 = textutil.encode_base64(fpath)
        self.check_OK(f"/fs_download?fpath={fpath_b64}")
        
        xauth.TestEnv.logout()
        try:
            token_info = SystemSyncTokenDao.upsert_by_holder("test", 60)
            self.check_OK(f"/fs_download?fpath={fpath_b64}&token={token_info.token}")
        finally:
            xauth.TestEnv.login_admin()

    def test_fs_download_large_file(self):
        # 回归测试：大文件（>10MB）下载时必须返回完整内容（200），
        # 不能因强制 206 分段只返回首段（4MB）导致文件残损。
        # 使用内存文件，避免向磁盘写入数十 MB 数据。
        size = 11 * 1024 * 1024  # 11MB
        fpath = "/__mem__/test_download_large.bin"
        with self.mock_file(fpath, b"\x00" * size):
            fpath_b64 = textutil.encode_base64(fpath)
            response = get_test_app().request(f"/fs_download?fpath={fpath_b64}&type=blob")
            self.assertEqual("200 OK", response.status, "大文件下载必须返回 200，而非 206 分段")
            self.assertEqual(size, len(response.data), "下载文件大小必须与源文件一致，不能被截断")
            self.assertNotIn("206", response.status)

    def test_fs_download_large_file_inline(self):
        # 客户端未发送 Range 时，无论内联还是下载都必须返回完整的 200 响应，
        # 不允许返回 206（206 仅允许作为对 Range 请求的响应，见 RFC 7233）
        size = 11 * 1024 * 1024  # 11MB
        fpath = "/__mem__/test_inline_large.bin"
        with self.mock_file(fpath, b"\x01" * size):
            fpath_b64 = textutil.encode_base64(fpath)
            response = get_test_app().request(f"/fs_download?fpath={fpath_b64}")
            self.assertEqual("200 OK", response.status)
            self.assertEqual(size, len(response.data))

    def test_fs_download_range_exact(self):
        size = 11 * 1024 * 1024  # 11MB
        fpath = "/__mem__/test_range_exact.bin"
        with self.mock_file(fpath, b"\x02" * size):
            fpath_b64 = textutil.encode_base64(fpath)
            url = f"/fs_download?fpath={fpath_b64}&type=blob"
            # 请求头部的 1KB 范围，必须精确返回 1024 字节
            response = get_test_app().request(url, headers={"Range": "bytes=0-1023"})
            self.assertEqual("206 Partial Content", response.status)
            self.assertEqual(1024, len(response.data))
            self.assertEqual("bytes 0-1023/%d" % size, response.headers.get("Content-Range"))

    def test_fs_download_range_no_4mb_cap(self):
        # 回归测试：read_range 必须严格按照客户端请求的区间返回，不能自行截断，
        # 否则拖动进度条/seek 时浏览器拿到的 Content-Range 比请求的小，无法播放
        size = 20 * 1024 * 1024  # 20MB，确保 8MB 范围能完整落在文件内
        fpath = "/__mem__/test_range_nocap.bin"
        with self.mock_file(fpath, b"\x03" * size):
            fpath_b64 = textutil.encode_base64(fpath)
            url = f"/fs_download?fpath={fpath_b64}&type=blob"
            # 请求 4MB 之后的 8MB 范围（跨越旧 4MB 上限）
            start = 4 * 1024 * 1024
            end = start + 8 * 1024 * 1024 - 1
            response = get_test_app().request(url, headers={"Range": f"bytes={start}-{end}"})
            self.assertEqual("206 Partial Content", response.status)
            # 必须返回完整的 8MB，而不是被截断成 4MB
            self.assertEqual(8 * 1024 * 1024, len(response.data))
            self.assertEqual(f"bytes {start}-{end}/{size}", response.headers.get("Content-Range"))

    def test_fs_download_range_open_ended(self):
        size = 11 * 1024 * 1024  # 11MB
        fpath = "/__mem__/test_range_open.bin"
        with self.mock_file(fpath, b"\x04" * size):
            fpath_b64 = textutil.encode_base64(fpath)
            url = f"/fs_download?fpath={fpath_b64}&type=blob"
            # 未指定结束位置，应返回到文件末尾
            start = 4 * 1024 * 1024
            response = get_test_app().request(url, headers={"Range": f"bytes={start}-"})
            self.assertEqual("206 Partial Content", response.status)
            self.assertEqual(size - start, len(response.data))
            self.assertEqual(f"bytes {start}-{size-1}/{size}", response.headers.get("Content-Range"))

    def test_fs_download_range_invalid(self):
        size = 11 * 1024 * 1024  # 11MB
        fpath = "/__mem__/test_range_invalid.bin"
        with self.mock_file(fpath, b"\x05" * size):
            fpath_b64 = textutil.encode_base64(fpath)
            url = f"/fs_download?fpath={fpath_b64}&type=blob"
            # 起始位置超出文件大小，应返回 416
            response = get_test_app().request(url, headers={"Range": "bytes=999999999-"})
            self.assertEqual("416 Range Not Satisfiable", response.status)

    def test_file_info(self):
        fpath = self.prepare_test_file("./test_info.txt", "test info")
        user_id = xauth.current_user_id()

        info = FileInfo()
        info.fpath = fpath
        info.user_id = user_id
        file_id = FileInfoDao.save_by_fpath(info)

        self.check_OK(f"/fs_upload/file_info?action=edit&file_id={file_id}")
        data = dict(
            action = "save",
            data = jsonutil.tojson(dict(
                file_id = file_id,
                remark = "update remark",
            ))
        )
        result = json_request_return_dict("/fs_upload/file_info", method="POST", data=data)
        assert result["success"]

        file_info = FileInfoDao.get_by_id(file_id=file_id, user_id=user_id)
        assert file_info != None
        assert file_info.remark == "update remark"
        
    def test_fs_zip(self):
        txt_file = get_test_file_path("./zip.txt")
        zip_file = get_test_file_path("./zip.zip")
        fsutil.writefile(txt_file, "hello,world")
        with ZipFile(zip_file, mode="w") as fp:
            fp.write(txt_file, arcname="zip.txt")
        
        zip_path_b64 = textutil.encode_base64(zip_file)
        self.check_OK(f"/fs/zip/{zip_path_b64}")
        self.check_OK(f"/fs/zip/{zip_path_b64}/zip.txt")