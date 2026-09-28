# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-22 00:17:06
@LastEditors  : xupingmao
@LastEditTime : 2024-05-19 17:20:25
@FilePath     : /xnote/handlers/fs/fs_api.py
@Description  : 文件API
"""

import os
import xutils
from xutils import webutil, dateutil, fsutil, textutil
from xnote.core import xauth, xtemplate

class FileConfigHandler:

    @xauth.login_required("admin")
    def POST(self):
        action = xutils.get_argument("action", "")

        if action == "sort":
            return self.update_sort()
        
        return dict(code = "error", message = "未知的action")

    def update_sort(self):
        order = xutils.get_argument("order", "")
        user_id = xauth.current_user_id()
        xauth.update_user_config(user_id, "fs_order", order)
        return webutil.SuccessResult()


class FileDetailHandler:

    def get_user_name_by_uid(self, uid=0):
        try:
            import pwd
            user_info = pwd.getpwuid(uid)
            if user_info != None:
                return user_info.pw_name
        except:
            pass
        return f"uid({uid})"
        
    def get_group_name_by_gid(self, gid=0):
        try:
            import grp
            group_info = grp.getgrgid(gid)
            if group_info != None:
                return group_info.gr_name
        except:
            pass
        return f"gid({gid})"

    @xauth.login_required("admin")
    def GET(self):
        fpath = xutils.get_argument_str("fpath")
        try:
            basename = os.path.basename(fpath)
            display_name = xutils.decode_name(basename)
            stat = os.stat(fpath)
            detail_msg = ""
            detail_msg += f"文件路径: {fpath}"
            detail_msg += f"\n展示名称: {display_name}"
            detail_msg += f"\n修改时间: {dateutil.format_datetime(stat.st_mtime)}"
            detail_msg += f"\n变更时间: {dateutil.format_datetime(stat.st_ctime)}"
            detail_msg += f"\n访问时间: {dateutil.format_datetime(stat.st_atime)}"
            detail_msg += f"\n文件大小: {fsutil.format_size(stat.st_size)}"
            detail_msg += f"\n用户: {self.get_user_name_by_uid(stat.st_uid)}"
            detail_msg += f"\n用户组: {self.get_group_name_by_gid(stat.st_gid)}"
            return webutil.SuccessResult(data=detail_msg)
        except:
            xutils.print_exc()
            return webutil.FailedResult(code="500", message="读取文件信息失败")

class FileOptionDialogHandler:
    """文件操作对话框的 HTML 片段，替代前端 art-template 渲染"""

    html = """
<div class="card dialog-body">
    <div class="align-center">
        <button class="btn btn-default fs-wide-btn" 
            data-path="{{filePath}}" 
            data-path-b64="{{filePathB64}}"
            onclick="xnote.action.fs.download(this);">下载</button>
        <button class="btn btn-default fs-wide-btn" 
            data-path="{{filePath}}" 
            data-name="{{fileName}}"
            data-realname="{{fileRealName}}"
            onclick="xnote.action.fs.rename(this);">重命名</button>
        <button class="btn btn-default fs-wide-btn"
            data-path="{{filePath}}"
            onclick="xnote.action.fs.move(this);">移动</button>
        <button class="btn btn-default fs-wide-btn"
            onclick="xnote.action.fs.copy(this);">复制</button>
        <button class="btn btn-default fs-wide-btn"
            data-path="{{filePath}}"
            onclick="xnote.action.fs.showDetail(this);">详细信息</button>
        <button class="btn btn-default fs-wide-btn"
            data-path="{{filePath}}"
            data-path-b64="{{filePathB64}}"
            onclick="xnote.action.fs.viewHex(this);">查看二进制</button>
        <button class="btn danger fs-wide-btn" 
            data-path="{{filePath}}"
            data-name="{{fileName}}"
            data-realname="{{fileRealName}}"
            onclick="xnote.action.fs.delete(this);">删除</button>
    </div>
</div>

<div class="dialog-footer">
    <div class="float-right">
        <button class="large btn-default" onclick="xnote.dialog.closeByElement(this)">关闭</button>
    </div>
</div>
"""

    @xauth.login_required("admin")
    def GET(self):
        path = xutils.get_argument_str("path", "")
        filePathB64 = textutil.encode_base64(path)
        fileName = xutils.decode_name(os.path.basename(path))
        fileRealName = fileName
        return xtemplate.render_text(self.html,
            filePath=textutil.html_escape(path),
            filePathB64=textutil.html_escape(filePathB64),
            fileName=textutil.html_escape(fileName),
            fileRealName=textutil.html_escape(fileRealName))


xurls = (
    r"/fs_api/config", FileConfigHandler,
    r"/fs_api/detail", FileDetailHandler,
    r"/fs/dialog/option", FileOptionDialogHandler,
)