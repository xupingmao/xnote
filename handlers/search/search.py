# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2022/04/16 18:03:13

import re
import time
import math
import web
import xutils
import typing
import handlers.note.dao as note_dao
import handlers.dict.dict_dao as dict_dao

from xnote.core import xconfig, xauth, xmanager, xtemplate, xnote_hooks
from xutils import textutil, u
from xutils import Storage
from xutils import dateutil
from xutils import mem_util
from xutils import six
from xnote.core.xtemplate import T
from xnote.core.models import SearchContext, SearchResult
from xnote.service.search_service import SearchHistoryDO
from xnote.plugin.tab import TabBox

SEARCH_TYPE_DICT = dict() # type: dict[str, Storage]

class SearchHandlerConfig:
    def __init__(self):
        self.search_type = ""
        self.placeholder = ""
        self.action = ""
        self.tag = ""

def register_search_handler(search_type, placeholder = None, action = None, tag = None):
    global SEARCH_TYPE_DICT

    if action is None:
        action = "/search"

    SEARCH_TYPE_DICT[search_type] = Storage(
        placeholder = placeholder,
        action = action,
        tag = tag
    )

def get_search_handler(search_type) -> Storage:
    handler = SEARCH_TYPE_DICT.get(search_type)
    if handler != None:
        return handler

    return SEARCH_TYPE_DICT.get("default")

# 注册到xtemplate的实现
xnote_hooks.get_search_handler = get_search_handler

class BaseRule:

    def __init__(self, pattern, func, scope="home"):
        self.pattern = pattern
        self.func    = func
        self.func_str = ""
        self.scope   = scope

def fill_note_info(files: typing.List[SearchResult]):
    ids = []
    for file in files:
        if file.category == "note":
            ids.append(file.parent_id)
    
    note_dict = note_dao.batch_query_dict(ids)
    for file in files:
        file.parent_name = ""
        parent = note_dict.get(file.parent_id)
        if parent is not None:
            file.parent_name = parent.name
        if file.category == "note":
            file.show_move = True

def log_search_history(user, key, category = "default", cost_time = 0):
    note_dao.add_search_history(user, key, category, cost_time)

@xutils.timeit(name = "Search.ListRecent", logargs = True, logfile = True)
def list_search_history(user_name, limit = -1):
    raw_history_list = note_dao.list_search_history(user_name)
    history_list = []

    for item in raw_history_list:
        if item.search_key not in history_list:
            history_list.append(item.search_key)
    return history_list

def build_search_context(user_name, category, key):
    words                   = textutil.split_words(key)
    ctx                     = SearchContext()
    ctx.key                 = key
    ctx.input_text          = key
    ctx.words               = words
    ctx.category            = category
    ctx.search_tool         = True
    ctx.search_message      = True
    ctx.search_note         = True
    ctx.search_note_content = False
    ctx.search_dict         = False
    ctx.user_name           = user_name
    ctx.user_id = xauth.UserDao.get_id_by_name(user_name)

    if category == "message":
        ctx.search_message = True
        ctx.search_note = False
        ctx.search_note_content = False
        ctx.search_tool = False
        ctx.search_dict_strict = False

    if ctx.category == "book":
        ctx.search_note = False
        ctx.search_tool = False
        ctx.search_dict_strict = False

    if category == "dict":
        ctx.search_dict = True
        ctx.search_dict_strict = False
        ctx.search_note = False
        ctx.search_tool = False

    if category == "content":
        ctx.search_note_content = True
        ctx.search_tool         = False
        ctx.search_message      = False
        ctx.search_dict_strict = False

    if category == "tool":
        ctx.search_tool = True
        ctx.search_dict_strict = False

    return ctx

class SearchHandler:

    def do_search(self, page_ctx: SearchContext, key, offset, limit):
        category    = xutils.get_argument_str("category", "")
        search_type = xutils.get_argument_str("search_type", "")
        user_name  = xauth.get_current_name()
        ctx = build_search_context(user_name, category, key)
        ctx.offset = offset
        ctx.limit = limit

        # 优先使用 search_type
        if search_type != None and search_type != "" and search_type != "default":
            ctx.offset = page_ctx.offset
            ctx.limit  = page_ctx.limit
            return self.do_search_by_type(ctx, key, search_type)
        
        return self.do_search_default(ctx)
    
    def do_search_default(self, ctx: SearchContext):
        key = ctx.key
        offset = ctx.offset
        limit = ctx.limit

        logger = mem_util.MemLogger("do_search")
        # 阻断性的搜索，比如特定语法的
        xmanager.fire("search.before", ctx)
        if ctx.stop:
            files = ctx.join_as_files()
            return files, len(files)

        logger.info("after fire search.before")

        # 普通的搜索行为
        xmanager.fire("search", ctx)

        logger.info("after fire search")

        ctx.files = RuleManager.apply(ctx, key)

        logger.info("after apply_search_rules")

        if ctx.stop:
            files = ctx.join_as_files()
            return files, len(files)

        # 慢搜索,如果时间过长,这个服务会被降级
        # TODO: 异步操作需要其他线程辅助执行
        xmanager.fire("search.slow", ctx)
        logger.info("after fire search.slow")
        xmanager.fire("search.after", ctx)
        logger.info("after fire search.after")

        search_result = ctx.join_as_files()
        fill_note_info(search_result)
        return search_result[offset:offset+limit], len(search_result)

    @mem_util.log_mem_info_deco("do_search_with_profile", log_args = True)
    def do_search_with_profile(self, page_ctx: SearchContext, key, offset, limit):
        user_name = xauth.current_name()
        category  = xutils.get_argument_str("category", "")
        search_type = xutils.get_argument_str("search_type", "")

        start_time = time.time()

        result = self.do_search(page_ctx, key, offset, limit)

        cost_time = int((time.time() - start_time) * 1000)

        if category == "":
            category = search_type

        log_search_history(user_name, key, category, cost_time)

        return result

    def do_search_dict(self, ctx: SearchContext, key):
        offset = ctx.offset
        limit  = ctx.limit
        notes, count = dict_dao.search_dict(key, offset, limit)
        return notes, count

    def do_search_note(self, ctx: SearchContext, key):
        user_name = xauth.current_name_str()
        parent_id = xutils.get_argument_int("parent_id")
        words = textutil.split_words(key)

        if ctx.category == "content":
            notes = note_dao.search_content(words, user_name)
        else:
            notes = note_dao.search_name(words, user_name, parent_id = parent_id)
        
        notes = [SearchResult(**item) for item in notes]
        for note in notes:
            note.category = "note"

        fill_note_info(notes)

        if parent_id != "" and parent_id != None:
            ctx.parent_note = note_dao.get_by_id(parent_id, include_full=False)

        offset = ctx.offset
        limit  = ctx.limit
        return notes[offset:offset+limit], len(notes)
    
    def do_search_message(self, ctx: SearchContext, key: str):
        from handlers.message.message_search import handle_search_event
        ctx.option.show_message_detail = True
        handle_search_event(ctx=ctx, tag_name="随手记")
        offset = ctx.offset
        limit = ctx.limit
        return ctx.messages[offset:offset+limit], len(ctx.messages)

    def do_search_task(self, ctx: SearchContext, key):
        import handlers.message.dao as MSG_DAO
        from handlers.message.dao import MessageDO
        from handlers.message.message_utils import process_message

        server_home = xconfig.WebConfig.server_home

        user_id = xauth.current_user_id()
        offset = ctx.offset
        limit  = ctx.limit

        search_tags = set(["task"])
        msg_list, amount = MSG_DAO.search_message(user_id, key, offset, limit, search_tags = search_tags)
        result = [] # type: list[SearchResult]
        search_task_link = SearchResult()
        search_task_link.icon = "hide"
        search_task_link.name = f"搜索到[{amount}]个待办"
        search_task_link.url = f"{server_home}/message?tag=task.search&key={xutils.quote(key)}"
        result.append(search_task_link)

        for msg_item in msg_list:
            process_message(msg_item)
            item = SearchResult(**msg_item)
            prefix = u("【待办】")

            if msg_item.tag == "done":
                prefix = u("【完成】")

            item.name = prefix + msg_item.ctime
            item.icon = "hide"
            item.url  = "#"
            result.append(item)
        
        # 统计已完成待办数量
        temp, done_count = MSG_DAO.search_message(user_id, key, search_tags = set(["done"]), count_only=True)
        if done_count > 0:
            done_summary = SearchResult()
            done_summary.icon = "hide"
            done_summary.name = "搜索到[%d]个已完成任务" % done_count
            done_summary.url =  f"{server_home}/message?tag=done.search&key={xutils.quote(key)}"
            result.append(done_summary)

        return result, amount

    def do_search_comment(self, ctx:SearchContext, key):
        from handlers.note import comment
        comment.search_comment_detail(ctx)
        return ctx.messages, len(ctx.messages)

    def do_search_by_type(self, ctx: SearchContext, key, search_type):
        if search_type == "note":
            return self.do_search_note(ctx, key)
        elif search_type == "dict":
            return self.do_search_dict(ctx, key)
        elif search_type == "task":
            return self.do_search_task(ctx, key)
        elif search_type == "message":
            return self.do_search_message(ctx, key)
        elif search_type == "comment":
            return self.do_search_comment(ctx, key)
        else:
            raise Exception(f"不支持的搜索类型:{search_type}")

    def GET(self, path_key = None):
        """search files by name and content"""
        RuleManager.load_rules()
        key         = xutils.get_argument_str("key", "")
        title       = xutils.get_argument_str("title", "")
        category    = xutils.get_argument_str("category", "default")
        page        = xutils.get_argument_int("page", 1)
        search_type = xutils.get_argument("search_type", "")
        page_url    =  f"/search/search?key={key}&category={category}&search_type={search_type}&page="
        pagesize    = xconfig.SEARCH_PAGE_SIZE
        offset      = (page-1) * pagesize
        limit       = pagesize
        ctx         = SearchContext()
        ctx.offset  = offset
        ctx.limit   = limit

        if path_key:
            key = xutils.unquote(path_key)

        if key == "" or key == None:
            raise web.found("/search/history")

        key = key.strip()

        files, count = self.do_search_with_profile(ctx, key, offset, pagesize)

        relevant_words = dict_dao.get_relevant_words(key)
        relevant_tab = TabBox(title="相关搜索", tab_key="key", css_class="btn-style")
        for word in relevant_words:
            relevant_tab.add_item(title=word, value=word)

        kw = Storage()
        kw.show_aside = True
        kw.category = category
        kw.html_title = "Search"
        kw.key = key
        kw.files = files
        kw.title = title
        kw.page_max = int(math.ceil(count/pagesize))
        kw.page_url = page_url
        kw.relevant_words = relevant_words
        kw.relevant_tab = relevant_tab

        return xtemplate.render("search/page/search_result.html", **kw)


class SearchHistoryHandler:

    def fetch_recent_logs(self, raw_history_list: typing.List[SearchHistoryDO]):
        history_list = []
        for item in raw_history_list:
            if item.search_key is None:
                continue
            if item.search_key not in history_list:
                history_list.append(item.search_key)
        return history_list
    
    def fetch_hot_logs(self, raw_history_list: typing.List[SearchHistoryDO], top_count = 10):
        count_dict = dict()

        for item in raw_history_list:
            count = count_dict.get(item.search_key, 0)
            count+=1
            count_dict[item.search_key] = count
        
        sorted_items = sorted(count_dict.items(), key = lambda x:x[1], reverse=True)
        return sorted_items[0:top_count]

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/search/history")
        note_dao.expire_search_history(user_name)

        raw_history_list = note_dao.list_search_history(user_name)

        kw = Storage()
        kw.show_aside = False
        kw.files = []
        kw.html_title = "Search"
        kw.recent = self.fetch_recent_logs(raw_history_list)
        kw.hot_logs = self.fetch_hot_logs(raw_history_list)
        kw.search_type = "default"

        return xtemplate.render("search/page/search_history.html", **kw)

    @xauth.login_required()
    def POST(self):
        p = xutils.get_argument("p", "")
        user_name = xauth.current_name()
        if p == "clear":
            note_dao.clear_search_history(user_name, search_type="default")
            return dict(code = "success")

        return dict(code = "500", message = "无效的操作")

class RuleManager:
    """搜索规则管理器"""

    is_loaded = False
    _RULES = []

    @classmethod
    def add_rule(cls, pattern, func_str):
        try:
            mod, func_name = func_str.rsplit('.', 1)
            # mod = __import__(mod, None, None, [''])
            mod = six._import_module("handlers.search." + mod)
            func = getattr(mod, func_name)
            func.modfunc = func_str
            rule = BaseRule(r"^%s\Z" % u(pattern), func)
            rule.func_str = func_str
            cls._RULES.append(rule)
        except Exception as e:
            xutils.print_exc()

    @classmethod
    def load_rules(cls):
        if cls.is_loaded:
            return

        cls.add_rule(r"([^ ]*)",  "api.search")
        cls.add_rule(r"静音(.*)", "mute.search")
        cls.add_rule(r"mute(.*)", "mute.search")
        cls.add_rule(r"取消静音",  "mute.cancel")
        cls.add_rule(r"(.*)", "note.search")
        cls.is_loaded = True

    @classmethod
    def apply(cls, ctx, key):
        files = []
        for rule in cls._RULES:
            pattern = rule.pattern
            func = rule.func
            # re.match内部已经实现了缓存
            m = re.match(pattern, key)
            if m:
                try:
                    logger = mem_util.MemLogger("rule:%r:%r" % (pattern, rule.func_str))

                    start_time0 = time.time()
                    results     = func(ctx, *m.groups())
                    cost_time0  = time.time() - start_time0
                    xutils.trace("SearchHandler", func.modfunc, int(cost_time0*1000))
                    if results is not None:
                        files += results
                    logger.done()
                except Exception as e:
                    xutils.print_exc()
        return files


class RulesHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        rules = list_search_rules(user_name)
        return xtemplate.render("search/search_rules.html", rules = rules, show_search = False)

def list_search_rules(user_name):
    import handlers.message.dao as msg_dao
    list, count = msg_dao.list_by_tag(user_name, 'key', 0, 1000)

    for item in list:
        item.url = "/note/timeline?type=search&key=" + xutils.encode_uri_component(item.content)
    return list


@xmanager.listen("sys.reload")
def reload_search(ctx = None):
    do_reload_search(ctx)

@xutils.log_init_deco("reload_search")
def do_reload_search(ctx = None):
    register_search_handler("plugin", placeholder = u"搜索插件", action = "/plugin_list")
    register_search_handler("note.public", placeholder = u"搜索公共笔记", action = "/note/timeline", tag = "public")
    register_search_handler("dict", placeholder = u"搜索词典", action = "/search")
    register_search_handler("message", placeholder = u"搜索随手记", action = "/message")
    register_search_handler("task", placeholder = u"搜索待办", action = "/search")
    register_search_handler("note", placeholder = u"搜索笔记", action = "/search")
    register_search_handler("comment", placeholder = u"搜索评论")
    register_search_handler("default", placeholder = u"综合搜索", action = "/search")
    register_search_handler("relevant_word", placeholder=u"搜索单词", action = "/dict/relevant/list")
    register_search_handler("checklist", placeholder=u"搜索清单列表", action="/note/checklist/search")
    register_search_handler("group_manage", placeholder=u"搜索笔记本", action="/note/group/manage")

class SearchDialogAjaxHandler:

    @xauth.login_required()
    def GET(self):
        key = xutils.get_argument_str("key", "")
        offset = xutils.get_argument_int("offset", 0)
        limit = xutils.get_argument_int("limit", 100)
        xutils.get_argument_str("callback", "")

        if key != "":
            searcher = SearchHandler()
            ctx = SearchContext()
            ctx.offset = offset
            ctx.limit = limit
            result, length = searcher.do_search(ctx, key, offset, limit)
            return xtemplate.render("search/ajax/search_dialog_detail.html", 
                result = result)
        return xtemplate.render("search/ajax/search_dialog.html")

xutils.register_func("search.list_rules", list_search_rules)
xutils.register_func("search.list_recent", list_search_history)
xutils.register_func("search.get_search_handler", get_search_handler)

xurls = (
    r"/search/search", SearchHandler, 
    r"/search"       , SearchHandler,
    r"/s/(.+)"       , SearchHandler,
    r"/search/history", SearchHistoryHandler,
    r"/search/rules", RulesHandler,
    r"/search/dialog", SearchDialogAjaxHandler,
)

