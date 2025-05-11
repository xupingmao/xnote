# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/06 12:48:09
# @modified 2022/04/16 17:40:40
# @filename message_utils.py

"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 20:04:59
@LastEditors  : xupingmao
@LastEditTime : 2024-08-24 22:20:53
@FilePath     : /xnote/handlers/message/message_utils.py
@Description  : 随手记工具
"""

import xutils
import web
import typing

from xnote.core import xconfig
from xnote.core.xtemplate import T
from xutils import textutil
from xutils import dateutil
from xutils import Storage
from xutils import u
from xutils import netutil
from xutils import webutil
from xutils.functions import Counter
from xutils.textutil import quote
from xutils.text_parser import TokenType
from xutils.text_parser import TextParser
from handlers.message.message_model import MessageFolder, MessageTag, is_task_tag
from xnote.core import xconfig
from xutils.text_parser import TextParser
from xutils.text_parser import set_img_file_ext
from xutils.text_parser import TextToken

from . import dao as msg_dao
from .message_model import MessageDO

MSG_DAO = xutils.DAO("message")
TAG_TEXT_DICT = dict(
    done="完成",
    cron="定期",
    task="任务",
    log="记事",
    key="话题",
    search="话题",
)
MAX_LIST_LIMIT = 1000


def success():
    return webutil.SuccessResult()


def failure(message, code="fail"):
    return webutil.FailedResult(code=code, message=message)


def build_search_url(keyword):
    key = quote(keyword)
    return u"/message?category=message&key=%s" % key


def build_search_html(content, search_tag="log"):
    fmt = u'<a href="{server_home}/message?tag=search&p={tag}&key={key}">{key_text}</a>'
    return fmt.format(tag=search_tag,
                      server_home=xconfig.WebConfig.server_home,
                      key=xutils.encode_uri_component(content),
                      key_text=xutils.html_escape(content))


def get_search_html(value="", tag=""):
    key0 = value
    key = value.strip()
    quoted_key = textutil.quote(key)
    value = textutil.escape_html(key0)
    server_home = xconfig.WebConfig.server_home
    return f"<a class=\"link\" href=\"{server_home}/message?tag={tag}&key={quoted_key}\">{value}</a>"

class TagHelper:

    search_tag_mapping = {
        "log":"search",
        "key":"search",
        "task":"task.search",
        "done":"done.search",
    }

    search_type_mapping = {
        "log":"message",
        "log.search":"message",
        "task.search":"task",
        "done.search":"task",
    }

    create_tag_mapping = {
        "todo": "task",
        "log.date": "log",
        "date": "log",
    }

    default_search_type = "message"

    @classmethod
    def get_search_tag(cls, tag):
        return cls.search_tag_mapping.get(tag, tag)
    
    @classmethod
    def get_search_type(cls, tag=""):
        return cls.search_type_mapping.get(tag, cls.default_search_type)
    
    @classmethod
    def get_create_tag(cls, tag=""):
        return cls.create_tag_mapping.get(tag, tag)

def mark_text(content, tag="log"):
    result = mark_text_v2(content, tag)
    return result.result_text, result.keywords

class MarkResult:
    def __init__(self, result_text="", keywords=set(), full_keywords=set()):
        self.result_text = result_text
        self.keywords = keywords
        self.full_keywords = full_keywords

class MarkTokenResult:
    def __init__(self, tokens: typing.List[TextToken]):
        self.tokens = tokens

def mark_text_v2(content="", tag="log"):
    # 设置图片文集后缀
    set_img_file_ext(xconfig.FS_IMG_EXT_LIST)

    tag=TagHelper.get_search_tag(tag)
    
    parser = TextParser()
    tokens = parser.parse_to_tokens(text=content)
    
    for token in tokens:
        if token.type in (TokenType.topic, TokenType.search):
            token.html = get_search_html(value=token.value, tag=tag)
  
    # parser.set_topic_translator(marker.mark)
    # parser.set_search_translator(marker.mark)

    keywords = parser.keywords
    if keywords == None:
        keywords = set()

    text_tokens = parser.get_text_tokens(tokens)
    return MarkResult("".join(text_tokens), keywords=get_standard_tag_set(keywords), full_keywords=keywords)

def mark_text_to_tokens(content="", tag="log"):
    parser = TextParser()
    tokens = parser.parse_to_tokens(text=content)
    return MarkTokenResult(tokens=tokens)

def process_message(message: MessageDO, search_tag="log"):
    parser = MessageListParser([])
    return parser.process_message(message)


def format_count(count):
    if count is None:
        return "0"
    if count >= 1000 and count < 10000:
        return '%0.1fk' % float(count / 1000)
    if count >= 1000 and count < 1000000:
        return '%dk' % int(count / 1000)
    if count > 1000000:
        return '%dm' % int(count / 1000000)
    # 保持类型一致
    return str(count)


def format_message_stat(stat):
    stat.task_count = format_count(stat.task_count)
    stat.done_count = format_count(stat.done_count)
    stat.cron_count = format_count(stat.cron_count)
    stat.log_count = format_count(stat.log_count)
    stat.search_count = format_count(stat.search_count)
    stat.key_count = format_count(stat.key_count)
    return stat


def do_split_date(date):
    year = dateutil.get_current_year()
    month = dateutil.get_current_month()
    day = dateutil.get_current_mday()

    if date == None or date == "":
        return year, month, day

    parts = date.split("-")
    if len(parts) >= 1:
        year = int(parts[0])
    if len(parts) >= 2:
        month = int(parts[1])
    if len(parts) >= 3:
        day = int(parts[2])
    return year, month, day


class TagSorter:

    def __init__(self):
        self.data = dict()

    def update(self, tag, mtime):
        old_mtime = self.data.get(tag)

        if mtime is None:
            mtime = ""

        if old_mtime is None:
            self.data[tag] = mtime
        else:
            self.data[tag] = max(old_mtime, mtime)

    def get_mtime(self, tag):
        return self.data.get(tag, "")


def get_tags_from_message_list(
        msg_list,
        input_tag="",
        input_date="",
        display_tag=None,
        search_tag="all") -> typing.List[MessageTag]:
    # type: (list[MessageDO], str, str, None|str, str) -> list[MessageTag]
    assert isinstance(msg_list, list)
    assert isinstance(input_tag, str)
    assert isinstance(input_date, str)

    tag_counter = Counter()
    tag_sorter = TagSorter()

    server_home = xconfig.WebConfig.server_home

    for msg_item in msg_list:
        process_message(msg_item)

        if msg_item.keywords is None:
            msg_item.keywords = set()

        if len(msg_item.keywords) == 0:
            tag_counter.incr("$no_tag")

        for tag in msg_item.keywords:
            tag_counter.incr(tag)
            tag_sorter.update(tag, msg_item.mtime)

    tag_list: typing.List[MessageTag] = []
    for tag_name in tag_counter.dict:
        amount = tag_counter.get_count(tag_name)
        no_tag = None
        is_no_tag = False
        search_key = tag_name

        if tag_name == "$no_tag":
            tag_name = "<无标签>"
            search_key = ""
            no_tag = "true"
            is_no_tag = True


        search_tag = TagHelper.get_search_tag(input_tag)

        params = dict(
            tag=search_tag,
            date=input_date,
            key=search_key,
            displayTag=display_tag,
            noTag=no_tag,
            p=search_tag,
        )

        query_string = netutil.build_query_string(params, skip_empty_value=True)
        url = f"{server_home}/message?{query_string}"            

        mtime = tag_sorter.get_mtime(tag_name)

        tag_item = MessageTag(tag_name=tag_name,
                              tag_code=tag_name,
                              tag=input_tag,
                              search_tag = search_tag,
                              amount=amount,
                              url=url,
                              mtime=mtime)
        tag_item.is_no_tag = is_no_tag
        tag_list.append(tag_item)

    tag_list.sort(key=lambda x: x.amount, reverse=True)

    return tag_list


def filter_default_content(content):
    if content == "":
        return content

    if content.endswith(" "):
        return content
    else:
        return content + " "


def is_system_tag(tag):
    assert isinstance(tag, str)
    return tag.startswith("$")

def is_standard_tag(tag):
    assert isinstance(tag, str)
    return tag.startswith("#") and tag.endswith("#")

def get_standard_tag_set(tags):
    # type: (set)->set
    return set(filter(is_standard_tag, tags))


def convert_message_list_to_day_folder(item_list, date, show_empty=False):
    result = []
    date_object = dateutil.parse_date_to_object(date)
    max_days = dateutil.get_days_of_month(date_object.year, date_object.month)
    today = dateutil.get_today()

    for i in range(max_days, 0, -1):
        temp_date = "%s-%02d-%02d" % (date_object.year, date_object.month, i)

        if temp_date > today:
            continue

        folder = MessageFolder()
        folder.date = temp_date
        folder.wday = dateutil.format_wday(temp_date)
        folder.item_list = []
        folder.title = "{folder.date} {folder.wday}".format(folder=folder)
        folder.css_class = ""
        if today == temp_date:
            folder.title += "【今天】"

        for item in item_list:
            if temp_date == dateutil.format_date(item.ctime):
                folder.item_list.append(item)

        if len(folder.item_list) == 0:
            folder.css_class = "gray-text"

        if show_empty or len(folder.item_list) > 0:
            result.append(folder)

    return result


def count_month_size(folder_list):
    result = 0
    for foler in folder_list:
        result += len(foler.item_list)

    return result


def get_length(item):
    if isinstance(item, (tuple, list, set, str)):
        return len(item)
    else:
        return -1


def filter_msg_list_by_key(msg_list, filter_key):
    result = []

    for msg_item in msg_list:
        process_message(msg_item)

        if filter_key == "$no_tag" and len(msg_item.keywords) == 0:
            result.append(msg_item)
        elif filter_key in msg_item.keywords:
            result.append(msg_item)

    return result

def list_by_date_and_key(user_id=0, month="", offset=0, limit=20, filter_key="", tag=""):
    date_start = ""
    date_end = ""
    if month != "":
        date_start = month + "-01"
        date_end = dateutil.date_str_add(date_start, months=1)
    else:
        raise Exception("month不能为空")
    
    list_limit = limit
    if filter_key != "":
        list_limit = MAX_LIST_LIMIT

    msg_list, amount = msg_dao.list_by_date_range(
                user_id=user_id, 
                offset=offset, 
                tag=tag,
                limit=list_limit, date_start=date_start, date_end=date_end)
    if filter_key == "":
        return msg_list, amount
    msg_list = filter_msg_list_by_key(msg_list, filter_key)
    return msg_list[offset:offset+limit], len(msg_list)


def filter_key(key: str) -> str:
    if key == None or key == "":
        return ""
    if key[0] == '#':
        return key

    if key[0] == '@':
        return key

    if key[0] == '《' and key[-1] == '》':
        return key

    return "#%s#" % key


def get_remote_ip():
    x_forwarded_for = web.ctx.env.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for != None:
        return x_forwarded_for.split(",")[0]
    return web.ctx.env.get("REMOTE_ADDR")


def get_similar_key(key: str):
    assert key != None
    if key.startswith("#"):
        key = key.lstrip("#")
        key = key.rstrip("#")
        return key
    else:
        return "#" + key + "#"


class MessageListParser(object):

    def __init__(self, chatlist: list, tag="log"):
        self.chatlist = chatlist
        self.tag = tag
        self.search_tag = TagHelper.get_search_tag(tag)

    def parse(self):
        self.do_process_message_list(self.chatlist)

    def prehandle_message(self, message):
        if message.status in (0, 50):
            # 兼容历史数据
            message.tag = "task"

        if message.status == 100:
            message.tag = "done"

        if message.tag == "cron":
            message.tag = "task"
        
        if message.tag == None:
            message.tag = self.tag

    def process_message(self, message: typing.Union[MessageDO, MessageTag]) -> Storage:
        self.prehandle_message(message)

        message.tag_text = TAG_TEXT_DICT.get(message.tag, message.tag)

        if message.content is None:
            message.content = ""
            return message
        
        if isinstance(message, MessageTag):
            message.html = build_search_html(message.content)
            return message

        result = mark_text_v2(message.content, message.tag)
        message.html = result.result_text
        message.keywords = result.keywords
        message.full_keywords = result.full_keywords

        if message.tag == "done":
            self.build_done_html(message)

        if message.tag == "key":
            self._build_keyword_html(message)

        return message

    def build_done_html(self, message: typing.Union[MessageDO, MessageTag]):
        task = None
        done_time = message.done_time
        if message.ref != None:
            task = msg_dao.get_message_by_id(message.ref)

        if task != None:
            html, keywords = mark_text(task.content, "done.search")
            message.html = u("完成任务:<blockquote>") + html + "</blockquote>"
            message.keywords = keywords
        elif done_time is None:
            done_time = message.mtime
            message.html += f"<br>------<br>完成于 {done_time}"

    def _build_keyword_html(self, message):
        if len(message.keywords) == 0:
            message.html = build_search_html(message.content)

    def do_process_message_list(self, message_list: typing.List[MessageDO]):
        keywords = {}
        for message in message_list:
            self.process_message(message)
            if message.keywords != None:
                for keyword in message.keywords:
                    count = keywords.get(keyword, 0)
                    keywords[keyword] = count + 1
            message.time_info = message.get_time_info()
            message.weekday = dateutil.datetime_to_weekday(message.time_info)

        self.keywords = []
        for word in keywords:
            amount = keywords[word]
            keyword_info = MessageTag(tag_name=word, tag_code=word, customized_url=build_search_url(word), amount=amount)
            self.keywords.append(keyword_info)

    def get_message_list(self):
        return self.chatlist

    def get_keywords(self):
        # type: () -> list[MessageTag]
        return self.keywords


class MessageKeyWordProcessor:
    def __init__(self, msg_list):
        assert isinstance(msg_list, list)
        self.msg_list = msg_list # type: list[MessageTag]

    def sort(self, orderby=""):
        msg_list = self.msg_list

        if orderby == "":
            return

        if orderby == "visit":
            msg_list.sort(key=lambda x: x.visit_cnt or 0, reverse=True)
            for item in msg_list:
                item.badge_info = "访问次数(%s)" % item.visit_cnt

        if orderby == "amount_desc":
            def amount_key_func(item: MessageTag):
                if isinstance(item.amount, str):
                    return 0
                if item.amount == None:
                    return 0
                return item.amount
            msg_list.sort(key=lambda x: x.content)
            msg_list.sort(key=amount_key_func, reverse=True)
            for item in msg_list:
                item.badge_info = "%s" % item.amount
            sort_keywords_by_marked(msg_list)

        if orderby == "recent":
            msg_list.sort(key=lambda x: x.mtime, reverse=True)
            for item in msg_list:
                item.badge_info = "%s" % xutils.format_date(item.mtime)

    def process(self):
        pass


def sort_tag_list(msg_list, orderby=""):
    p = MessageKeyWordProcessor(msg_list)
    p.sort(orderby)


def sort_keywords_by_marked(msg_list: typing.List[MessageTag]):
    msg_list.sort(key=lambda x:x.score, reverse=True)


def list_hot_tags(user_name:str, limit=20):
    assert isinstance(user_name, str)

    msg_list = msg_dao.MsgTagInfoDao.list(user=user_name, offset=0, limit=MAX_LIST_LIMIT)
    sort_tag_list(msg_list, "amount_desc")
    server_home = xconfig.WebConfig.server_home
    for msg in msg_list:
        msg.customized_url = f"{server_home}/message?tag=log.search&key={quote(msg.content)}"
    return msg_list[:limit]


def list_task_tags(user_name="", limit=20, offset=0, tag="task"):
    assert isinstance(user_name, str)

    msg_list, amount = msg_dao.list_task(
        user_name, offset=0, limit=MAX_LIST_LIMIT)
    return get_tags_from_message_list(msg_list, display_tag="taglist", input_tag=tag)

def is_marked_keyword(user_name, keyword):
    obj = msg_dao.get_by_content(user_name, "key", keyword)
    return obj != None and obj.is_marked

def check_content_for_update(user_name, tag, content):
    if tag == 'key':
        return msg_dao.get_by_content(user_name, tag, content)
    return None


def touch_key_by_content(user_name, tag, content):
    item = msg_dao.MsgTagInfoDao.get_first(user_name=user_name, content=content)
    if item != None:
        item.mtime = xutils.format_datetime()
        if item.visit_cnt is None:
            item.visit_cnt = 0
        item.visit_cnt += 1
        msg_dao.MsgTagInfoDao.update(item)
    return item

def format_tag_list(tag_list: typing.List[MessageTag], search_tag="log"):
    for item in tag_list:
        item.html = build_search_html(item.tag_code, search_tag=search_tag)
    return tag_list

xutils.register_func("message.list_hot_tags", list_hot_tags)
xutils.register_func("message.filter_default_content", filter_default_content)
