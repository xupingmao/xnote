# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/06 12:48:09
# @modified 2021/11/22 23:25:33
# @filename message_utils.py
import xutils
import web
from xtemplate import T
from xutils import textutil
from xutils import dateutil
from xutils import Storage
from xutils import u
from xutils.functions import Counter
from xutils.textutil import escape_html
from xutils.textutil import quote
from handlers.message.message_class import MessageFolder

MSG_DAO = xutils.DAO("message")
TAG_TEXT_DICT = dict(
    done = "完成",
    cron = "定期",
    task = "任务",
    log  = "记事",
    key  = "话题",
    search = "话题",
)

def success():
    return dict(success = True, code = "success")

def failure(message, code = "fail"):
    return dict(success = False, code = code, message = message)

def build_search_url(keyword):
    key = quote(keyword)
    return u"/message?category=message&key=%s" % key


def build_search_html(content):
    fmt = u'<a href="/message?key=%s">%s</a>'
    return fmt % (xutils.encode_uri_component(content), xutils.html_escape(content))

def build_done_html(message):
    task = None
    done_time = message.done_time

    if message.ref != None:
        task = MSG_DAO.get_by_id(message.ref)

    if task != None:
        html, keywords = mark_text(task.content)
        message.html = u("完成任务:<br>&gt;&nbsp;") + html
        message.keywords = keywords
    elif done_time is None:
        done_time = message.mtime
        message.html += u("<br>------<br>完成于 %s") % done_time

def do_mark_topic(parser, key0):
    key = key0.lstrip("")
    key = key.rstrip("")
    quoted_key = textutil.quote(key)
    value = textutil.escape_html(key0)
    token = "<a class=\"link\" href=\"/message?key=%s\">%s</a>" % (quoted_key, value)
    parser.tokens.append(token)


def mark_text(content):
    import xconfig
    from xutils.text_parser import TextParser
    from xutils.text_parser import set_img_file_ext
    # 设置图片文集后缀
    set_img_file_ext(xconfig.FS_IMG_EXT_LIST)

    parser = TextParser()
    parser.set_topic_marker(do_mark_topic)

    tokens = parser.parse(content)
    return "".join(tokens), parser.keywords

def process_tag_message(message):
    message.html = build_search_html(message.content)

    if message.amount is None:
        message.amount = T("更新中...")

def process_message(message):
    if message.status == 0 or message.status == 50:
        # 兼容历史数据
        message.tag = "task"
    if message.status == 100:
        message.tag = "done"

    if message.tag == "cron":
        message.tag = "task"

    message.tag_text = TAG_TEXT_DICT.get(message.tag, message.tag)

    if message.content is None:
        message.content = ""
        return message

    if message.tag == "key" or message.tag == "search":
        process_tag_message(message)
    else:
        html, keywords = mark_text(message.content)
        message.html = html
        message.keywords = keywords

    if message.tag == "done":
        build_done_html(message)

    if message.keywords is None:
        message.keywords = set()

    return message


def fuzzy_item(item):
    item = item.replace("'", "''")
    return "'%%%s%%'" % item

def get_status_by_code(code):
    if code == "created":
        return 0
    if code == "suspended":
        return 50
    if code == "done":
        return 100
    return 0

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
    stat.log_count  = format_count(stat.log_count)
    stat.search_count = format_count(stat.search_count)
    stat.key_count    = format_count(stat.key_count)
    return stat


def do_split_date(date):
    year  = dateutil.get_current_year()
    month = dateutil.get_current_month()
    day   = dateutil.get_current_mday()

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


def get_tags_from_message_list(msg_list, input_tag = "", input_date = ""):
    tag_counter = Counter()
    tag_sorter = TagSorter()

    for msg_item in msg_list:
        process_message(msg_item)
        
        if msg_item.keywords is None:
            msg_item.keywords = set()

        if len(msg_item.keywords) == 0:
            tag_counter.incr("$no_tag")

        for tag in msg_item.keywords:
            tag_counter.incr(tag)
            tag_sorter.update(tag, msg_item.mtime)

            
    tag_list = []
    for tag_name in tag_counter.dict:
        amount = tag_counter.get_count(tag_name)
        # url = "/message?searchTags=%s&key=%s" % (input_tag, textutil.encode_uri_component(tag_name))

        encoded_tag = textutil.encode_uri_component(tag_name)

        if input_date == "":
            url = "/message?tag=%s&filterKey=%s&filterDate=%s" % (input_tag, encoded_tag, input_date)
        else:
            url = "/message?tag=%s&date=%s&filterKey=%s" % (input_tag, input_date, encoded_tag)

        if tag_name == "$no_tag":
            tag_name = "<无标签>"
            # url = "/message?tag=search&searchTags=%s&noTag=true" % input_tag

        mtime = tag_sorter.get_mtime(tag_name)

        tag_item = Storage(name = tag_name, 
            tag = input_tag, 
            amount = amount, 
            url = url, 
            mtime = mtime)
        tag_list.append(tag_item)

    tag_list.sort(key = lambda x: x.amount, reverse = True)

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

def convert_message_list_to_day_folder(item_list, date, show_empty = False):
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
        folder.title = f"{folder.date} {folder.wday}"
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

def filter_key(key):
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


def get_similar_key(key):
    assert key != None
    if key.startswith("#"):
        key = key.lstrip("#")
        key = key.rstrip("#")
        return key
    else:
        return "#" + key + "#"


class MessageListParser(object):

    def __init__(self, chatlist):
        self.chatlist = chatlist

    def parse(self):
        self.do_process_message_list(self.chatlist)

    def do_process_message_list(self, message_list):
        keywords = set()
        for message in message_list:
            process_message(message)
            if message.keywords != None:
                keywords = message.keywords.union(keywords)
        
        self.keywords = []
        for word in keywords:
            keyword_info = Storage(name = word, url = build_search_url(word))
            self.keywords.append(keyword_info)

    def get_message_list(self):
        return self.chatlist

    def get_keywords(self):
        return self.keywords


xutils.register_func("message.filter_default_content", filter_default_content)
