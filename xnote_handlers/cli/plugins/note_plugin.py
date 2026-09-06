# -*- coding: utf-8 -*-
"""笔记相关的服务端 CLI 命令（远程命令）

这些命令在【服务端】执行，通过 xnote_cli.register_cmd 注册。CLI 客户端在登录后
从 /api/cli/command_list 获取远程命令列表，并通过 /api/cli/run 转发执行。

与页面 REST 接口不同，这里直接调用 note 模块内部的 dao / service 逻辑，避免
服务端自己再发起一次 HTTP 请求。鉴权基于当前请求登录用户（/api/cli/run 本身
带 @xauth.login_required）。

错误通过 xnote_cli.XnoteCliError 抛出，由 RunApiHandler 转换为失败响应。
"""
import xnote_cli
import xutils
from xnote_cli import XnoteCliContext, XnoteCliError
from xnote.core import xauth
from xutils import textutil
from xnote_handlers.note import dao
from xnote_handlers.note.note_edit import update_and_notify
from xnote_handlers.note.dao_delete import delete_note


def _check_note_auth(note, user_id):
    # type: (object, int) -> None
    if note is None:
        raise XnoteCliError("笔记不存在")
    if note.creator_id != user_id and getattr(note, "is_public", 0) != 1:
        raise XnoteCliError("无权限访问该笔记")


def note_view_handler(ctx):
    # type: (XnoteCliContext) -> object
    if len(ctx.args) < 1:
        raise XnoteCliError("用法: xnote-cli note-view <id>")
    note_id = ctx.args[0]
    note = dao.get_by_id(note_id)
    _check_note_auth(note, xauth.current_user_id())
    return note.content


def note_search_handler(ctx):
    # type: (XnoteCliContext) -> object
    if len(ctx.args) < 1:
        raise XnoteCliError("用法: xnote-cli note-search <关键词>")
    key = " ".join(ctx.args)
    limit = 20
    user_name = xauth.current_name_str()
    user_id = xauth.current_user_id()
    words = textutil.split_words(key)
    result = []  # type: list
    if len(words) == 0:
        return result
    for item in dao.search_name(words=words, creator=user_name, limit=limit):
        result.append(dict(id=item.note_id, name=item.name,
                          type="group" if item.is_group else "note",
                          url=item.url))
    for item in dao.search_content(words=words, creator_id=user_id, limit=limit):
        result.append(dict(id=item.id, name=item.name, type=item.type, url=item.url))
    return result


def note_edit_handler(ctx):
    # type: (XnoteCliContext) -> object
    if len(ctx.args) < 1:
        raise XnoteCliError("用法: xnote-cli note-edit <id> <content>")
    note_id = ctx.args[0]
    content = " ".join(ctx.args[1:])
    old = dao.get_by_id(note_id)
    _check_note_auth(old, xauth.current_user_id())
    update_kw = dict(content=content, data="", size=len(content),
                    mtime=xutils.format_datetime(), version=old.version + 1)
    update_and_notify(old, update_kw)
    return "已更新: " + old.get_url()


def note_delete_handler(ctx):
    # type: (XnoteCliContext) -> object
    if len(ctx.args) < 1:
        raise XnoteCliError("用法: xnote-cli note-delete <id>")
    note_id = ctx.args[0]
    old = dao.get_by_id(note_id)
    _check_note_auth(old, xauth.current_user_id())
    delete_note(note_id)
    return "已删除: " + str(note_id)


def note_list_handler(ctx):
    # type: (XnoteCliContext) -> object
    """按父文档 id 列出子文档列表

    - 无参数或参数为 0：等价于 /note/group，列出根目录下的笔记本（group）
    - 指定父文档 id：列出该父文档下的全部子项（笔记 + 子笔记本）
    """
    if len(ctx.args) == 0:
        parent_id = 0
    else:
        try:
            parent_id = int(ctx.args[0])
        except ValueError:
            raise XnoteCliError("用法: xnote-cli note-list <父文档id>，参数需为数字")
        if parent_id < 0:
            raise XnoteCliError("父文档 id 不能为负数")

    user_name = xauth.current_name_str()
    if parent_id == 0:
        # 根目录：等价于 /note/group，只列笔记本（group）
        notes = dao.list_by_parent(user_name, parent_id=0, offset=0,
                                   limit=1000, orderby="name")
        notes = [n for n in notes if n.type == "group"]
    else:
        # 指定父文档：列出其下的全部子项（笔记 + 子笔记本）
        notes = dao.list_by_parent(user_name, parent_id=parent_id, offset=0,
                                   limit=1000, orderby="name")

    result = []  # type: list
    for item in notes:
        result.append(dict(id=item.note_id, name=item.name, type=item.type,
                           parent_id=item.parent_id, url=item.url))
    return result


xnote_cli.register_cmd("note-view", note_view_handler, "查看笔记内容")
xnote_cli.register_cmd("note-search", note_search_handler, "搜索笔记")
xnote_cli.register_cmd("note-edit", note_edit_handler, "编辑笔记内容")
xnote_cli.register_cmd("note-delete", note_delete_handler, "删除笔记")
xnote_cli.register_cmd("note-list", note_list_handler, "按父文档id列出子文档列表")
