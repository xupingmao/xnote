# -*- coding:utf-8 -*-
# @since 2026/09/18
# 评论模块（统一笔记 / 待办 / 清单等场景）
#
# 笔记与待办的评论能力完全一致, 仅通过 `type` 区分(`todo_task`),
# 待办评论额外用不相交的 target_id 区间(COMMENT_TARGET_OFFSET)与笔记隔离。
# 这里把查询、渲染、更新接口集中实现, 各业务页面(todo/note)只负责传入不同的
# `type` / `target_id` / `save_url`, 无需各自实现一套评论逻辑。
import math
import typing
import web
import urllib.parse
from urllib.parse import quote

import xutils

from typing import List, Optional, TYPE_CHECKING
from xnote.core import xconfig
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xutils import webutil
from xutils import dateutil
from xutils import textutil
from xutils import Storage
from xnote.core.xtemplate import T
from xnote.core.models import SearchContext, SearchResult
from . import dao_comment
from xnote_handlers.note import dao as note_dao
from xnote_handlers.note.note_service import NoteService
from xnote_handlers.note.dao import NoteIndexDao
from xnote_handlers.note.models import NoteTypeInfo

# CommentBox 是纯 UI 组件(位于 webui), 这里仅弹窗页面复用, 不构成 webui 对
# xnote_handlers 的依赖(依赖方向: xnote_handlers.comment -> webui.comment)。
from xnote.webui.comment import CommentBox

if TYPE_CHECKING:
    from .dao_comment import CommentVO


# ---------------------------------------------------------------------------
# 笔记 / 待办评论的隔离约定
# ---------------------------------------------------------------------------
COMMENT_TYPE = "todo_task"

# 评论表按 target_id 查询、不按 type 过滤（note 模块的历史设计），
# 而 note_id 与 task_id 是两套独立自增序列，直接复用会串号（甚至跨用户泄露）。
# 这里把待办评论的 target_id 映射到一个不相交的区间，彻底避免与笔记/清单冲突。
COMMENT_TARGET_OFFSET = 10 ** 10


def to_comment_target_id(task_id: int) -> int:
    """task_id -> 评论表的 target_id"""
    return COMMENT_TARGET_OFFSET + task_id


def to_task_id(comment_target_id: int) -> int:
    """评论表的 target_id -> task_id"""
    return comment_target_id - COMMENT_TARGET_OFFSET


# ---------------------------------------------------------------------------
# 评论列表渲染（查询 + 服务端渲染 HTML 片段）
# ---------------------------------------------------------------------------
def get_page_max(count):
    return int(math.ceil(count / xconfig.PAGE_SIZE))


def translate_search(key0: str):
    key = key0.lstrip("")
    key = key.rstrip("")
    quoted_key = textutil.quote(key)
    value = textutil.escape_html(key0)
    fmt = "<a class=\"link\" href=\"/search?search_type=comment&key={quoted_key}\">{value}</a>"
    return fmt.format(quoted_key=quoted_key, value=value)


def mark_text(content):
    from xutils.text_parser import TextParser
    from xutils.text_parser import set_img_file_ext
    from xutils.text_parser import TokenType
    # 设置图片文集后缀
    set_img_file_ext(xconfig.FS_IMG_EXT_LIST)

    parser = TextParser()
    tokens = parser.parse_to_tokens(content)

    for token in tokens:
        if token.type in (TokenType.topic, TokenType.search):
            token.html = translate_search(token.value)

    text_tokens = parser.get_text_tokens(tokens)
    return "".join(text_tokens)


def process_comments(comments: "typing.List[CommentVO]", show_note: bool = False):
    for comment in comments:
        if comment.content is None:
            continue
        comment.html = mark_text(comment.content)

        if show_note:
            note = note_dao.get_by_id(comment.note_id, include_full=False)
            if note != None:
                comment.note_name = note.name
                comment.note_url = note.url
            elif comment.type == COMMENT_TYPE:
                # 待办评论：comment.note_id 是评论表 target_id（=偏移量+task_id）
                # 来源为待办任务，名称可能较长需截断，完整内容放到 note_title 供 hover 查看
                from xnote_handlers.todo.dao import TodoDao
                task = TodoDao.get_by_id(to_task_id(comment.note_id))
                if task != None:
                    comment.note_title = task.content
                    comment.note_name = textutil.get_short_text(task.content, 20)
                    comment.note_url = "/todo/detail?task_id=%s" % task.task_id

        # 获取被回复的用户信息
        if comment.ref_user_id > 0:
            ref_user_name = xauth.UserDao.get_name_by_id(comment.ref_user_id)
            comment.ref_user = ref_user_name or ""


def _to_text(html):
    """xtemplate.render 返回 bytes, 命令的 value 需要是文本"""
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


def build_comment_page_url() -> str:
    """构造评论分页的基础URL, 保留当前请求的其它参数, 不含分页参数。

    评论分页参数是 comment_page(而非 page), 避免与页面自身分页参数冲突。
    """
    query = web.ctx.get("query", "") or ""
    if query.startswith("?"):
        query = query[1:]
    params = urllib.parse.parse_qs(query, keep_blank_values=True)
    params.pop("comment_page", None)
    params.pop("page", None)
    if params:
        return "?" + urllib.parse.urlencode(params, doseq=True)
    return ""


def render_to_html(
    comments: "List[CommentVO]", show_note: bool = False, page: int = 1, page_max: int = 1,
    show_edit: bool = False, note_user_id: int = 0,
    comment_delete_url: str = "/comment/delete") -> str:
    return _to_text(xtemplate.render("comment/page/comment_list_ajax.html",
        show_comment_edit=show_edit,
        page=page,
        page_max=page_max,
        page_url=build_comment_page_url(),
        page_arg_name="comment_page",
        comments=comments,
        show_note=show_note,
        note_user_id=note_user_id,
        comment_delete_url=comment_delete_url,
        fragment=True))


def render_comment_list_html(target_id: int, list_type: str = "note_id",
                             list_date: str = "", show_note: bool = False,
                             show_edit: bool = False,
                             comment_order: Optional[str] = None,
                             page: Optional[int] = None,
                             comment_type: str = "") -> str:
    """服务端渲染评论列表 HTML 片段(不含 #comments 外层容器), 供模板初次渲染直接使用,
    逻辑与 CommentListAjaxHandler(GET, resp_type=html) 保持一致。

    评论组件被笔记和待办共用: 待办评论通过不相交的 target_id 区间(COMMENT_TARGET_OFFSET)
    与笔记/清单隔离, 据此区分后分别按是否带 type 过滤、并使用各自的删除地址。

    comment_order / comment_page 默认从当前请求参数读取(支持 x-tab 排序、分页导航),
    显式传入时以参数为准。
    """
    page_size = xconfig.PAGE_SIZE
    if comment_order is None:
        comment_order = xutils.get_argument_str("comment_order", "latest")
    if page is None:
        page = xutils.get_argument_int("comment_page", 1)

    user_info = xauth.current_user()
    user_name = user_info.name if user_info else ""
    user_id = user_info.user_id if user_info else 0
    offset = max(0, page - 1) * page_size
    note_user_id = 0
    comment_delete_url = "/comment/delete"
    comments: typing.List[CommentVO] = []
    count = 0

    is_todo = comment_type == COMMENT_TYPE

    if list_type == "user":
        if user_id == 0:
            return render_to_html([], show_note=show_note, page=page,
                                  page_max=1, show_edit=show_edit,
                                  note_user_id=note_user_id,
                                  comment_delete_url=comment_delete_url)
        count = dao_comment.count_comments_by_user(user_id, list_date)
        comments = dao_comment.list_comments_by_user(user_id=user_id, date=list_date,
                                                      offset=offset, limit=page_size,
                                                      order=comment_order)
    elif list_type == "search":
        key = xutils.get_argument_str("key", "")
        keywords = textutil.split_words(key)
        comments = dao_comment.search_comment(user_name=user_name, keywords=keywords,
                                              limit=1000, note_id=target_id)
        count = len(comments)
    elif is_todo:
        comments, count = dao_comment.list_parent_comments(
            target_id, offset=offset, limit=page_size,
            user_name=user_name, order=comment_order, type=COMMENT_TYPE)
        note_user_id = 0
        comment_delete_url = "/comment/delete"
    else:
        note_index = NoteIndexDao.get_by_id(target_id)
        if note_index is None:
            return render_to_html([], show_note=show_note, page=page,
                                  page_max=1, show_edit=show_edit,
                                  note_user_id=note_user_id,
                                  comment_delete_url=comment_delete_url)
        comments, count = dao_comment.list_parent_comments(
            target_id, offset=offset, limit=page_size,
            user_name=user_name, order=comment_order)
        note_user_id = note_index.creator_id

    page_max = get_page_max(count)
    process_comments(comments, show_note)
    return render_to_html(comments, show_note=show_note, page=page, page_max=page_max,
                          show_edit=show_edit, note_user_id=note_user_id,
                          comment_delete_url=comment_delete_url)


def build_refresh_commands(message: str = "", delay: int = 500) -> webutil.CommandsResult:
    """评论新增/编辑/删除后的统一返回: 提示 toast + 延迟刷新页面。

    不重建评论列表 HTML —— 页面上可能存在其它随评论变化的区域(评论数、待办统计等),
    直接刷新页面最简单可靠; 延迟是为了让用户先看到 toast 提示。
    """
    result = webutil.CommandsResult()
    if message:
        result.add_toast_command(value=message)
    result.add_reload_command(delay=delay)
    return result


# ---------------------------------------------------------------------------
# 搜索
# ---------------------------------------------------------------------------
def search_comment_summary(ctx: SearchContext):
    comments = dao_comment.search_comment(user_name=ctx.user_name, keywords=ctx.words)
    if len(comments) > 0:
        result = SearchResult()
        result.name = "搜索到[%s]条评论" % len(comments)
        result.url = "/search?key=%s&search_type=comment" % quote(ctx.key)
        result.icon = "fa-comments-o"
        result.show_more_link = True
        ctx.messages.append(result)


def search_comment_detail(ctx: SearchContext):
    """搜索评论详细列表接口"""
    result = []
    comments = dao_comment.search_comment(user_name=ctx.user_name, keywords=ctx.words)

    process_comments(comments, show_note=True)

    for item in comments:
        item.icon = "fa-comment-o"
        item.name = "[评论] %s" % item.note_name
        item.url = item.note_url
        # 转换为可读时间字符串
        if item.create_time > 0:
            item.mtime = dateutil.format_datetime(item.create_time, is_ms=True)
            item.ctime = item.mtime
        result.append(item)

    ctx.messages += result


@xmanager.searchable(r".+")
def on_search_comments(ctx: SearchContext):
    if ctx.category == "default":
        search_comment_summary(ctx)

    if ctx.category == "comment":
        search_comment_detail(ctx)


# ---------------------------------------------------------------------------
# 评论查询 / 保存 / 删除 接口（笔记与待办共用, 通过 type / target_id 区分）
# ---------------------------------------------------------------------------
class CommentListAjaxHandler:
    """评论列表（返回 HTML 片段或 JSON）
    笔记与待办共用: 待办评论的 target_id 落在不相交区间, 据此校验归属并走 todo 分支渲染。"""

    def GET(self):
        note_id = xutils.get_argument_int("note_id")
        list_type = xutils.get_argument_str("list_type")
        resp_type = xutils.get_argument_str("resp_type")
        list_date = xutils.get_argument_str("list_date")
        show_note = xutils.get_argument_bool("show_note")
        show_edit = xutils.get_argument_bool("show_edit")
        comment_order = xutils.get_argument_str("comment_order")
        comment_type = xutils.get_argument_str("type")
        # 评论分页参数为 comment_page, 避免与页面自身的 page(如笔记分页)冲突
        page = xutils.get_argument_int("comment_page", 1)
        page_max = 1
        page_size = xconfig.PAGE_SIZE
        user_info = xauth.current_user()
        user_name = ""
        user_id = 0
        note_user_id = 0

        # can visit comment without login
        if user_info != None:
            user_name = user_info.name
            user_id = user_info.user_id

        offset = max(0, page - 1) * page_size

        # 用显式 type 区分笔记/待办(笔记 id 为 13 位时间戳, 可能 >= 旧的不相交区间,
        # 不能再用 target_id 区间判断, 否则会把笔记评论误判为待办)
        is_todo = comment_type == COMMENT_TYPE

        if is_todo:
            from xnote_handlers.todo.dao import TodoDao
            # 待办评论：校验待办归属（避免越权查看他人待办评论）
            task = TodoDao.get_by_id(to_task_id(note_id), user_id=user_id)
            if task is None:
                return webutil.FailedResult(message="待办不存在")
        elif list_type not in ("user", "search"):
            # 笔记评论：校验访问权限
            note_index = NoteIndexDao.get_by_id(note_id)
            if note_index is None:
                raise Exception("笔记不存在")
            share_token = xutils.get_argument_str("share_token")
            NoteService.check_auth(note_index, user_id=user_id, share_token=share_token)

        if list_type == "user":
            if user_id == 0:
                raise Exception("请先登录")
            count = dao_comment.count_comments_by_user(user_id, list_date)
            comments = dao_comment.list_comments_by_user(user_id=user_id,
                date=list_date, offset=offset,
                limit=page_size, order=comment_order)
        elif list_type == "search":
            comments = self.search_comments(user_name)
            count = len(comments)
        else:
            comments, count = dao_comment.list_parent_comments(note_id, offset=offset, limit=page_size,
                                                  user_name=user_name, order=comment_order)
            if not is_todo and user_info is not None:
                note_index = NoteIndexDao.get_by_id(note_id)
                if note_index is not None:
                    note_user_id = note_index.creator_id

        page_max = get_page_max(count)

        # 处理评论列表
        process_comments(comments, show_note)

        if resp_type == "html":
            comment_delete_url = "/comment/delete"
            return render_to_html(
                comments, show_note, page=page, page_max=page_max, show_edit=show_edit,
                note_user_id=note_user_id, comment_delete_url=comment_delete_url)
        else:
            return comments

    def search_comments(self, user_name):
        key = xutils.get_argument_str("key", "")
        note_id = xutils.get_argument("note_id", "")
        keywords = textutil.split_words(key)
        return dao_comment.search_comment(user_name=user_name, keywords=keywords, limit=1000, note_id=note_id)


class SaveCommentAjaxHandler:
    """发表评论（笔记 / 待办共用, 通过 type 区分是否需要同步待办统计）"""

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument_int("note_id")
        content = xutils.get_argument_str("content")
        comment_type = xutils.get_argument_str("type")
        user_info = xauth.current_user()
        files = xutils.get_list_argument("files[]")
        parent_comment_id = xutils.get_argument_int("parent_comment_id")
        ref_comment_id = xutils.get_argument_int("ref_comment_id")
        ref_user_id = xutils.get_argument_int("ref_user_id")

        if user_info is None:
            return webutil.FailedResult(code="403", message="请登录进行操作~")

        if note_id == 0:
            return webutil.FailedResult(message="note_id参数为空")

        if content == "" and len(files) == 0:
            return webutil.FailedResult(code="400", message="content参数为空")

        # 用显式 type 区分笔记/待办(type="todo_task"), 不依赖 target_id 区间
        # (笔记 id 为 13 位时间戳, 会超过旧的不相交区间, 区间判断会误判)
        is_todo = comment_type == COMMENT_TYPE

        comment = dao_comment.CommentVO()
        comment.user = user_info.name
        comment.user_id = user_info.id
        comment.type = COMMENT_TYPE if is_todo else comment_type
        comment.content = content
        comment.note_id = note_id
        comment.files = files
        comment.parent_comment_id = parent_comment_id
        comment.ref_comment_id = ref_comment_id
        comment.ref_user_id = ref_user_id

        dao_comment.create_comment(comment)

        if is_todo:
            # 待办评论：同步更新时间 + 评论数
            from xnote_handlers.todo.dao import TodoDao
            task = TodoDao.get_by_id(to_task_id(note_id))
            if task is not None:
                task.update_time = dateutil.timestamp_ms()
                task.comment_count = dao_comment.count_comment_by_note(note_id, type=COMMENT_TYPE)
                TodoDao.update(task)
        else:
            note_dao.touch_note(note_id)

        # 不再重建评论列表 HTML, 只提示 + 延迟刷新页面(重新加载评论列表)
        return build_refresh_commands(message="评论成功")


class DeleteCommentAjaxHandler:
    """删除评论（笔记 / 待办共用）"""

    def GET(self):
        return self.POST()

    @xauth.login_required()
    def POST(self):
        comment_id = xutils.get_argument_int("comment_id")
        user = xauth.current_name()
        comment = dao_comment.get_comment(comment_id)
        if comment is None:
            dao_comment.delete_index(comment_id)
            return webutil.SuccessResult()
        if user != comment.user:
            return webutil.FailedResult(message="unauthorized")

        # 用评论记录自身的 type 区分笔记/待办(不依赖 target_id 区间)。
        # 旧数据可能把笔记评论误标为 todo_task, 而对应待办并不存在(脏数据);
        # 此时不应阻断删除 —— 只要 user_id 一致(上面的 user 校验已通过),
        # 就允许删除评论本身, 仅跳过 todo 评论数回写。
        is_todo = comment.type == COMMENT_TYPE

        if is_todo:
            from xnote_handlers.todo.dao import TodoDao
            task = TodoDao.get_by_id(to_task_id(int(comment.note_id)),
                                     user_id=xauth.current_user_id())
            if task is None:
                # 待办不存在(脏数据 / 已删除): 不阻断, 按普通评论删除即可
                is_todo = False

        dao_comment.delete_comment(comment_id)

        if is_todo:
            # 重新统计评论数（含回复）写回 todo_task
            target_id = int(comment.note_id)
            new_count = dao_comment.count_comment_by_note(target_id, type=COMMENT_TYPE)
            TodoDao.update_comment_count(to_task_id(target_id), new_count)

        return build_refresh_commands(message="删除成功")


class MyCommentsHandler:
    """我的评论页面"""

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/comment/mine")
        date = xutils.get_argument_str("date", "")

        kw = Storage()
        kw.show_comment_title = False
        kw.show_comment_create = False
        kw.show_comment_note = True
        kw.comment_list_date = date
        kw.comment_list_type = "user"
        kw.note_type = "comment"
        kw.type_list = NoteTypeInfo.get_type_list()
        # 评论列表由前端初始化时通过独立接口异步加载(组件本身不查询 DB),
        # 这里仅配置 list_type / list_date 等参数(经 CommentBox 注入 data-* 属性)
        return xtemplate.render("comment/page/comment_user_page.html", **kw)


class CommentEditHandler:
    """评论编辑对话框（GET 返回编辑表单 HTML 片段）"""

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        comment_id = xutils.get_argument_int("comment_id")
        comment = dao_comment.get_comment(comment_id)
        if comment is None:
            return "评论不存在"
        if comment.user != user_name:
            return "无操作权限"
        return xtemplate.render("comment/page/comment_edit_dialog.html", comment=comment)


class CommentUpdateHandler:
    """提交评论更新（POST）"""

    @xauth.login_required()
    def POST(self):
        user_name = xauth.current_name()
        comment_id = xutils.get_argument_int("comment_id")
        version = xutils.get_argument_int("version", 0)
        comment = dao_comment.get_comment(comment_id)
        if comment is None:
            return webutil.FailedResult(code="404", message="评论不存在")
        if comment.user != user_name:
            return webutil.FailedResult(code="403", message="无权限操作")
        content = xutils.get_argument_str("content", "")
        date = xutils.get_argument_str("date")
        update_ctime = False
        if date:
            # create_time 是毫秒时间戳
            import datetime
            old_datetime = datetime.datetime.fromtimestamp(comment.create_time / 1000)
            old_date_str = old_datetime.strftime("%Y-%m-%d")
            if date != old_date_str:
                # 构建新的时间字符串并转换为毫秒时间戳
                new_datetime_str = f"{date} {old_datetime.strftime('%H:%M:%S')}"
                new_datetime = dateutil.parse_datetime(new_datetime_str)
                comment.create_time = int(new_datetime * 1000)
                update_ctime = True
        comment.content = content
        comment.files = xutils.get_list_argument("files[]")
        comment.version = version
        try:
            dao_comment.CommentDao.update(comment, update_ctime=update_ctime)
        except ValueError as e:
            return webutil.FailedResult(code="400", message=str(e))
        return build_refresh_commands(message="更新成功")


class UpdatePinLevelHandler:
    """置顶 / 取消置顶评论"""

    @xauth.login_required()
    def POST(self):
        comment_id = xutils.get_argument_int("comment_id")
        pin_level = xutils.get_argument_int("pin_level")
        user_id = xauth.current_user_id()
        comment_index = dao_comment.CommentDao.get_index_by_id(comment_id=comment_id)
        if comment_index is None:
            return webutil.FailedResult("404", message="评论不存在")
        note_index = NoteIndexDao.get_by_id(note_id=comment_index.target_id)
        if note_index is None:
            return webutil.FailedResult("404", message="笔记不存在")
        if note_index.creator_id != user_id:
            return webutil.FailedResult("401", message="没有操作权限")
        comment_index.pin_level = pin_level
        dao_comment.CommentDao.update_index(comment_index)
        return webutil.SuccessResult()


class CommentRepliesAjaxHandler:
    """获取评论的回复列表"""

    def GET(self):
        note_id = xutils.get_argument_int("note_id")
        parent_comment_id = xutils.get_argument_int("parent_comment_id")
        page = xutils.get_argument_int("page", 1)
        page_size = xutils.get_argument_int("page_size", 20)

        if note_id == 0 or parent_comment_id == 0:
            return webutil.FailedResult(message="参数错误")

        offset = max(0, page - 1) * page_size
        replies, total = dao_comment.list_replies(note_id, parent_comment_id, offset, page_size)

        # 处理评论内容
        process_comments(replies, show_note=False)

        return webutil.SuccessResult(data={
            "replies": replies,
            "total": total,
            "page": page,
            "page_size": page_size
        })


class CommentReplyListHandler:
    """获取评论回复列表（返回HTML片段）"""

    def GET(self):
        note_id = xutils.get_argument_int("note_id")
        parent_comment_id = xutils.get_argument_int("parent_comment_id")

        if note_id == 0 or parent_comment_id == 0:
            return "参数错误"

        replies, total = dao_comment.list_replies(note_id, parent_comment_id, offset=0, limit=100)
        process_comments(replies, show_note=False)

        return xtemplate.render("comment/page/comment_reply_list.html",
            replies=replies,
            total=total)


class CommentReplyDialogHandler:
    """回复对话框页面"""

    def GET(self):
        note_id = xutils.get_argument_int("note_id")
        parent_comment_id = xutils.get_argument_int("parent_comment_id")
        ref_comment_id = xutils.get_argument_int("ref_comment_id")
        ref_user_id = xutils.get_argument_int("ref_user_id")
        ref_user = xutils.get_argument_str("ref_user")

        if note_id == 0 or parent_comment_id == 0:
            return "参数错误"

        return xtemplate.render("comment/page/comment_reply_dialog.html",
            note_id=note_id,
            parent_comment_id=parent_comment_id,
            ref_comment_id=ref_comment_id,
            ref_user_id=ref_user_id,
            ref_user=ref_user)


class TodoCommentDialogHandler:
    """待办评论弹窗页面（供 iframe 弹窗加载，复用统一评论组件）"""

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        task_id = xutils.get_argument_int("task_id", 0)
        from xnote_handlers.todo.dao import TodoDao
        task = TodoDao.get_by_id(task_id, user_id=user_id)
        if task is None:
            raise web.seeother("/todo")

        kw = Storage()
        kw.title = T("评论")
        kw.html_title = T("评论")
        # 弹窗页面：去掉导航和侧边栏
        kw.show_nav = False
        kw.show_menu = False
        kw.show_aside = False
        # 评论组件（复用，type=todo_task + 独立 target_id 空间隔离；
        # 列表由前端初始化时通过独立接口异步加载，不再服务端静态输出）
        kw.comment_box = CommentBox(
            target_id=to_comment_target_id(task_id),
            list_type="note_id",
            show_edit=True,
            title=T("评论"),
            create_type=COMMENT_TYPE,
            save_url="/comment/save",
            list_url="/comment/list",
        )
        return xtemplate.render("todo/page/todo_comment_dialog.html", **kw)


xutils.register_func("note.search_comment_detail", search_comment_detail)


xurls = (
    # 评论接口统一前缀 /comment/*（笔记 / 待办 / 清单共用, 通过 type + 独立 target_id 区间区分）
    r"/comment/list", CommentListAjaxHandler,
    r"/comment/save", SaveCommentAjaxHandler,
    r"/comment/delete", DeleteCommentAjaxHandler,
    r"/comment/edit", CommentEditHandler,
    r"/comment/update", CommentUpdateHandler,
    r"/comment/mine", MyCommentsHandler,
    r"/comment/update_pin_level", UpdatePinLevelHandler,
    r"/comment/replies", CommentRepliesAjaxHandler,
    r"/comment/reply_list", CommentReplyListHandler,
    r"/comment/reply_dialog", CommentReplyDialogHandler,
    r"/comment/dialog", TodoCommentDialogHandler,
)
