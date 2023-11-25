# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2022/04/16 18:03:13

import re
import time
import math
import web
import xutils
from xnote.core import xconfig, xauth, xmanager, xtemplate, xnote_hooks
import handlers.note.dao as note_dao
import handlers.dict.dict_dao as dict_dao
from xutils import textutil, u
from xutils import Storage
from xutils import dateutil
from xutils import mem_util
from xutils import six
from xnote.core.xtemplate import T

NOTE_DAO = xutils.DAO("note")
MSG_DAO  = xutils.DAO("message")
DICT_DAO = xutils.DAO("dict")

config = xconfig
SEARCH_TYPE_DICT = dict() # type: dict[str, Storage]


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
        self.scope   = scope

class SearchContext:

    def __init__(self):
        # 输入的文本
        self.key              = ''
        self.input_text       = ''
        self.words = [] # 根据key分割的token
        self.category = "" # 搜索类型
        # 正则匹配的分组
        self.groups           = []
        self.user_name        = ''
        self.search_message   = False
        self.search_note      = True
        self.search_note_content = False
        self.search_dict      = False
        # 精确搜索字典
        self.search_dict_strict = True
        self.search_tool      = True
        # 是否继续执行，用于最后兜底的搜索，一般是性能消耗比较大的
        self.stop             = False
        
        # 处理的结果集，优先级: 系统功能 > 字典 > 个人数据
        self.commands = [] # 命令
        self.tools    = [] # 工具
        self.dicts    = [] # 词典 -- 公共
        self.messages = [] # 待办/记事/通知/评论
        self.notes    = [] # 笔记
        self.files    = [] # 文件

        # 分页信息
        self.offset = 1
        self.limit = 20

    def join_as_files(self):
        return self.commands + self.tools + self.dicts + self.messages + self.notes + self.files

def fill_note_info(files):
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
        file.show_move = True
        file.badge_info = "热度:%s" % file.hot_index

def log_search_history(user, key, category = "default", cost_time = 0):
    note_dao.add_search_history(user, key, category, cost_time)

@xutils.timeit(name = "Search.ListRecent", logargs = True, logfile = True)
def list_search_history(user_name, limit = -1):
    raw_history_list = note_dao.list_search_history(user_name)
    history_list = []

    for item in raw_history_list:
        if item.key is None:
            continue
        if item.key not in history_list:
            history_list.append(item.key)
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

    def do_search(self, page_ctx, key, offset, limit):
        category    = xutils.get_argument("category", "")
        search_type = xutils.get_argument("search_type", "")
        words      = textutil.split_words(key)
        user_name  = xauth.get_current_name()
        ctx        = build_search_context(user_name, category, key)

        logger = mem_util.MemLogger("do_search")

        # 优先使用 search_type
        if search_type != None and search_type != "" and search_type != "default":
            ctx.offset = page_ctx.offset
            ctx.limit  = page_ctx.limit
            return self.do_search_by_type(ctx, key, search_type)
        
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

        page_ctx.tools = []
        
        search_result = ctx.join_as_files()
        
        fill_note_info(search_result)

        return search_result[offset:offset+limit], len(search_result)

    @mem_util.log_mem_info_deco("do_search_with_profile", log_args = True)
    def do_search_with_profile(self, page_ctx, key, offset, limit):
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

    def do_search_dict(self, ctx, key):
        offset = ctx.offset
        limit  = ctx.limit
        notes, count = dict_dao.search_dict(key, offset, limit)
        for note in notes:
            note.raw = note.value
            note.icon = "hide"
        return notes, count

    def do_search_note(self, ctx, key):
        user_name = xauth.current_name_str()
        parent_id = xutils.get_argument_int("parent_id")
        words = textutil.split_words(key)
        notes = note_dao.search_name(words, user_name, parent_id = parent_id)
        for note in notes:
            note.category = "note"
            note.mdate = dateutil.format_date(note.mtime)
        fill_note_info(notes)

        if parent_id != "" and parent_id != None:
            ctx.parent_note = note_dao.get_by_id(parent_id)

        offset = ctx.offset
        limit  = ctx.limit
        return notes[offset:offset+limit], len(notes)

    def do_search_task(self, ctx, key):
        user_name = xauth.get_current_name()
        offset = ctx.offset
        limit  = ctx.limit

        search_tags = set(["task"])
        item_list, amount = MSG_DAO.search(user_name, key, offset, limit, search_tags = search_tags)

        for item in item_list:
            MSG_DAO.process_message(item)
            prefix = u("待办 - ")

            if item.tag == "done":
                prefix = u("完成 - ")

            item.name = prefix + item.ctime
            item.icon = "hide"
            item.url  = "#"
        
        # 统计已完成待办数量
        temp, done_count = MSG_DAO.search(user_name, key, search_tags = set(["done"]), count_only=True)
        if done_count > 0:
            done_summary = Storage()
            done_summary.icon = "hide"
            done_summary.name = "已完成任务[%d]" % done_count
            done_summary.url =  "/message?tag=search&p=done&key=%s" % xutils.quote(key)
            item_list.insert(0, done_summary)

        return item_list, amount

    def do_search_comment(self, ctx, key):
        NOTE_DAO.search_comment_detail(ctx)
        return ctx.messages, len(ctx.messages)

    def do_search_by_type(self, ctx, key, search_type):
        if search_type == "note":
            return self.do_search_note(ctx, key)
        elif search_type == "dict":
            return self.do_search_dict(ctx, key)
        elif search_type == "task":
            return self.do_search_task(ctx, key)
        elif search_type == "comment":
            return self.do_search_comment(ctx, key)
        else:
            raise Exception("不支持的搜索类型:%s" % search_type)

    def GET(self, path_key = None):
        """search files by name and content"""
        RuleManager.load_rules()
        key         = xutils.get_argument_str("key", "")
        title       = xutils.get_argument("title", "")
        category    = xutils.get_argument("category", "default")
        page        = xutils.get_argument_int("page", 1)
        search_type = xutils.get_argument("search_type", "")
        user_name   = xauth.get_current_name()
        page_url    =  "/search/search?key={key}&category={category}&search_type={search_type}&page=".format(**locals())
        pagesize    = xconfig.SEARCH_PAGE_SIZE
        offset      = (page-1) * pagesize
        limit       = pagesize
        ctx         = Storage()
        ctx.offset  = offset
        ctx.limit   = limit

        if path_key:
            key = xutils.unquote(path_key)

        if key == "" or key == None:
            raise web.found("/search/history")

        key = key.strip()

        files, count = self.do_search_with_profile(ctx, key, offset, pagesize)

        return xtemplate.render("search/page/search_result.html", 
            show_aside = False,
            key = key,
            html_title = "Search",
            category = category,
            files    = files, 
            title    = title,
            page_max = int(math.ceil(count/pagesize)),
            page_url = page_url,
            **ctx)


class SearchHistoryHandler:

    def fetch_recent_logs(self, raw_history_list):
        history_list = []
        for item in raw_history_list:
            if item.key is None:
                continue
            if item.key not in history_list:
                history_list.append(item.key)
        return history_list
    
    def fetch_hot_logs(self, raw_history_list, top_count = 10):
        count_dict = dict()

        for item in raw_history_list:
            count = count_dict.get(item.key, 0)
            count+=1
            count_dict[item.key] = count
        
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
            note_dao.clear_search_history(user_name)
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
    list, count = MSG_DAO.list_by_tag(user_name, 'key', 0, 1000)

    for item in list:
        item.url = "/note/timeline?type=search&key=" + xutils.encode_uri_component(item.content)
    return list


@xmanager.listen("sys.reload")
def reload_search(ctx = None):
    do_reload_search(ctx)

@xutils.log_init_deco("reload_search")
def do_reload_search(ctx = None):
    register_search_handler("plugin", placeholder = u"搜索插件", action = "/plugins_list")
    register_search_handler("note.public", placeholder = u"搜索公共笔记", action = "/note/timeline", tag = "public")
    register_search_handler("dict", placeholder = u"搜索词典", action = "/search")
    register_search_handler("message", placeholder = u"搜索随手记", action = "/message")
    register_search_handler("task", placeholder = u"搜索待办", action = "/message")
    register_search_handler("note", placeholder = u"搜索笔记", action = "/search")
    register_search_handler("comment", placeholder = u"搜索评论")
    register_search_handler("default", placeholder = u"综合搜索", action = "/search")
    register_search_handler("relevant_word", placeholder=u"搜索单词", action = "/dict/relevant/list")
    register_search_handler("checklist", placeholder=u"搜索清单列表", action="/note/checklist/search")
    register_search_handler("group_manage", placeholder=u"搜索笔记本", action="/note/group/manage")

class SearchDialogAjaxHandler:

    @xauth.login_required()
    def GET(self):
        key = xutils.get_argument("key", "")
        offset = xutils.get_argument("offset", 0, type = int)
        limit = xutils.get_argument("limit", 100, type = int)
        xutils.get_argument("callback", "")

        if key != "":
            searcher = SearchHandler()
            ctx = Storage()
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

