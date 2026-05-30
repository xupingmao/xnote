# encoding=utf-8
# Tests for xnote_handlers.message.message_utils

from . import test_base
from .test_base import BaseTestCase

import xutils
from xutils import Storage
from xutils import dateutil

from xnote_handlers.message.message_utils import (
    TagHelper,
    format_count,
    do_split_date,
    filter_default_content,
    format_filter_key,
    get_similar_key,
    parse_tags_to_list,
    parse_filter_config,
    is_system_tag,
    is_standard_tag,
    is_user_tag_or_heading,
    get_user_tag_or_heading_set,
    get_standard_tag_set,
    get_length,
    sort_keywords_by_marked,
    mark_text,
    mark_text_v2,
    MarkResult,
    filter_msg_list_by_key,
    filter_msg_list_by_keys,
    convert_message_list_to_day_folder,
    MessageListParser,
    MessageKeyWordProcessor,
    count_month_size,
    format_message_stat,
    list_hot_tags,
    format_tag_list,
    build_search_html,
    build_tag_html,
    touch_key_by_content,
    get_tags_from_message_list,
)
from xnote_handlers.message.message_model import (
    MessageDO, MsgTagInfo, MessageTag,
    MessageStatDO, MessageStatVO,
    MessageFolder, TagFilterConfig,
    QuerySourceType,
)
from xnote_handlers.message.message_model import MessageTagEnum
from xnote.service.tag_service import TagPrefixEnum
from xnote.core import xconfig

import typing


class TestFormatCount(BaseTestCase):
    """测试 format_count 函数"""

    def test_format_count_none(self):
        self.assertEqual("0", format_count(None))

    def test_format_count_zero(self):
        self.assertEqual("0", format_count(0))

    def test_format_count_under_1000(self):
        self.assertEqual("999", format_count(999))

    def test_format_count_1000_to_9999(self):
        self.assertEqual("1.0k", format_count(1000))
        self.assertEqual("5.5k", format_count(5500))
        # 9999/1000=9.999 -> rounds to 10.0k
        self.assertEqual("10.0k", format_count(9999))

    def test_format_count_10000_to_999999(self):
        self.assertEqual("10k", format_count(10000))
        self.assertEqual("100k", format_count(100000))
        self.assertEqual("999k", format_count(999000))

    def test_format_count_1m_and_over(self):
        # 1,000,000 falls through (no `<=` on million condition); 10,000,000 works
        self.assertEqual("1000000", format_count(1000000))
        self.assertEqual("10m", format_count(10000000))


class TestDoSplitDate(BaseTestCase):
    """测试 do_split_date 函数"""

    def test_split_none(self):
        year, month, day = do_split_date(None)
        self.assertIsInstance(year, int)
        self.assertIsInstance(month, int)
        self.assertIsInstance(day, int)

    def test_split_empty(self):
        year, month, day = do_split_date("")
        self.assertIsInstance(year, int)
        self.assertIsInstance(month, int)
        self.assertIsInstance(day, int)

    def test_split_year_only(self):
        year, month, day = do_split_date("2024")
        self.assertEqual(2024, year)

    def test_split_year_month(self):
        year, month, day = do_split_date("2024-03")
        self.assertEqual(2024, year)
        self.assertEqual(3, month)

    def test_split_full_date(self):
        year, month, day = do_split_date("2024-03-15")
        self.assertEqual(2024, year)
        self.assertEqual(3, month)
        self.assertEqual(15, day)


class TestFilterDefaultContent(BaseTestCase):
    """测试 filter_default_content 函数"""

    def test_empty_string(self):
        self.assertEqual("", filter_default_content(""))

    def test_ends_with_space(self):
        self.assertEqual("hello ", filter_default_content("hello "))

    def test_no_trailing_space(self):
        self.assertEqual("hello ", filter_default_content("hello"))


class TestTagDetection(BaseTestCase):
    """测试标签检测函数"""

    def test_is_system_tag(self):
        self.assertTrue(is_system_tag("$tag"))
        self.assertFalse(is_system_tag("#tag#"))
        self.assertFalse(is_system_tag("tag"))

    def test_is_standard_tag(self):
        self.assertTrue(is_standard_tag("#tag#"))
        self.assertTrue(is_standard_tag("#multi word#"))
        self.assertFalse(is_standard_tag("#tag"))
        self.assertFalse(is_standard_tag("tag#"))
        self.assertFalse(is_standard_tag("$tag"))

    def test_is_user_tag_or_heading(self):
        self.assertTrue(is_user_tag_or_heading("#tag#"))
        heading_val = TagPrefixEnum.heading.value
        self.assertTrue(is_user_tag_or_heading(heading_val + "title"))
        self.assertFalse(is_user_tag_or_heading("#tag"))
        self.assertFalse(is_user_tag_or_heading("tag"))
        self.assertFalse(is_user_tag_or_heading("$system"))

    def test_get_user_tag_or_heading_set(self):
        heading_val = TagPrefixEnum.heading.value
        input_set = set(["#tag1#", "#tag2#", "plain", heading_val + "h1"])
        result = get_user_tag_or_heading_set(input_set)
        expected = set(["#tag1#", "#tag2#", heading_val + "h1"])
        self.assertEqual(expected, result)

    def test_get_standard_tag_set(self):
        input_set = set(["#tag1#", "#tag2#", "plain", "#incomplete"])
        result = get_standard_tag_set(input_set)
        self.assertEqual(set(["#tag1#", "#tag2#"]), result)


class TestFormatFilterKey(BaseTestCase):
    """测试 format_filter_key 函数"""

    def test_none_or_empty(self):
        self.assertEqual("", format_filter_key(None))
        self.assertEqual("", format_filter_key(""))

    def test_already_hashtag(self):
        self.assertEqual("#key#", format_filter_key("#key#"))

    def test_at_user(self):
        self.assertEqual("@user", format_filter_key("@user"))

    def test_book_title(self):
        self.assertEqual("《book》", format_filter_key("《book》"))

    def test_plain_key(self):
        self.assertEqual("#plain#", format_filter_key("plain"))


class TestGetSimilarKey(BaseTestCase):
    """测试 get_similar_key 函数"""

    def test_heading_prefix(self):
        heading_val = TagPrefixEnum.heading.value
        self.assertEqual(heading_val + "title", get_similar_key(heading_val + "title"))

    def test_hashtag_strips_marks(self):
        self.assertEqual("key", get_similar_key("#key#"))

    def test_plain_to_hashtag(self):
        self.assertEqual("#key#", get_similar_key("key"))

    def test_strip_extra_hashes(self):
        self.assertEqual("key", get_similar_key("##key##"))


class TestParseTagsToList(BaseTestCase):
    """测试 parse_tags_to_list 函数"""

    def test_none_or_empty(self):
        self.assertEqual([], parse_tags_to_list(None))
        self.assertEqual([], parse_tags_to_list(""))

    def test_space_separated(self):
        result = parse_tags_to_list("a b c")
        self.assertEqual(["a", "b", "c"], result)

    def test_comma_separated(self):
        result = parse_tags_to_list("a,b,c")
        self.assertEqual(["a", "b", "c"], result)

    def test_newline_separated(self):
        result = parse_tags_to_list("a\nb\nc")
        self.assertEqual(["a", "b", "c"], result)

    def test_mixed_separators(self):
        result = parse_tags_to_list("a b,c\nd")
        self.assertEqual(["a", "b", "c", "d"], result)

    def test_duplicates_removed(self):
        result = parse_tags_to_list("a b a c b")
        self.assertEqual(["a", "b", "c"], result)

    def test_extra_spaces_handled(self):
        result = parse_tags_to_list("a   b  c")
        self.assertEqual(["a", "b", "c"], result)


class TestParseFilterConfig(BaseTestCase):
    """测试 parse_filter_config 函数"""

    def test_empty_config(self):
        config = parse_filter_config("")
        self.assertEqual([], config.tag1)
        self.assertEqual([], config.tag2)
        self.assertEqual([], config.tag3)

    def test_none_config(self):
        config = parse_filter_config(None)
        self.assertEqual([], config.tag1)
        self.assertEqual([], config.tag2)
        self.assertEqual([], config.tag3)

    def test_legacy_text_format(self):
        config = parse_filter_config("tag1 tag2 tag3")
        self.assertEqual(["tag1", "tag2", "tag3"], config.tag1)
        self.assertEqual([], config.tag2)
        self.assertEqual([], config.tag3)

    def test_json_format(self):
        json_str = '{"tag1": ["a", "b"], "tag2": ["c"], "tag3": ["d"]}'
        config = parse_filter_config(json_str)
        self.assertEqual(["a", "b"], config.tag1)
        self.assertEqual(["c"], config.tag2)
        self.assertEqual(["d"], config.tag3)

    def test_invalid_json_falls_back_to_text(self):
        # invalid JSON falls through to legacy text parsing
        config = parse_filter_config("{invalid}")
        self.assertEqual(["{invalid}"], config.tag1)

    def test_json_with_missing_keys(self):
        json_str = '{"tag1": ["a"]}'
        config = parse_filter_config(json_str)
        self.assertEqual(["a"], config.tag1)
        self.assertEqual([], config.tag2)
        self.assertEqual([], config.tag3)


class TestTagHelper(BaseTestCase):
    """测试 TagHelper 类"""

    def test_get_search_tag(self):
        self.assertEqual("search", TagHelper.get_search_tag("log"))
        self.assertEqual("search", TagHelper.get_search_tag("key"))
        self.assertEqual("task.search", TagHelper.get_search_tag("task"))
        self.assertEqual("done.search", TagHelper.get_search_tag("done"))
        self.assertEqual("custom", TagHelper.get_search_tag("custom"))

    def test_get_search_type(self):
        self.assertEqual("message", TagHelper.get_search_type("log"))
        self.assertEqual("message", TagHelper.get_search_type("log.search"))
        self.assertEqual("task", TagHelper.get_search_type("task.search"))
        self.assertEqual("task", TagHelper.get_search_type("done.search"))
        self.assertEqual("message", TagHelper.get_search_type("unknown"))

    def test_get_create_tag(self):
        self.assertEqual("task", TagHelper.get_create_tag("todo"))
        self.assertEqual("log", TagHelper.get_create_tag("log.date"))
        self.assertEqual("log", TagHelper.get_create_tag("date"))
        self.assertEqual("custom", TagHelper.get_create_tag("custom"))


class TestGetLength(BaseTestCase):
    """测试 get_length 函数"""

    def test_list_length(self):
        self.assertEqual(3, get_length([1, 2, 3]))

    def test_tuple_length(self):
        self.assertEqual(2, get_length((1, 2)))

    def test_set_length(self):
        self.assertEqual(2, get_length(set([1, 2])))

    def test_str_length(self):
        self.assertEqual(5, get_length("hello"))

    def test_non_iterable(self):
        self.assertEqual(-1, get_length(42))


class TestSortKeywordsByMarked(BaseTestCase):
    """测试 sort_keywords_by_marked 函数"""

    def make_tag(self, tag_code, score=0.0):
        tag = MsgTagInfo(tag_code=tag_code)
        tag.score = score
        return tag

    def test_marked_first(self):
        tags = [
            self.make_tag("#a#", 0.0),
            self.make_tag("#b#", 1.0),
            self.make_tag("#c#", 0.5),
        ]
        sort_keywords_by_marked(tags)
        self.assertEqual(1.0, tags[0].score)
        self.assertEqual(0.5, tags[1].score)
        self.assertEqual(0.0, tags[2].score)


class TestMarkText(BaseTestCase):
    """测试 mark_text / mark_text_v2 函数"""

    def test_empty_content(self):
        html, keywords = mark_text("", "log")
        self.assertEqual("", html)
        self.assertEqual(set(), keywords)

    def test_plain_text(self):
        html, keywords = mark_text("hello world", "log")
        # spaces are encoded to &nbsp;
        self.assertIn("hello", html)
        self.assertIn("world", html)
        self.assertEqual(set(), keywords)

    def test_hashtag_extraction(self):
        html, keywords = mark_text("#tag1# hello", "log")
        self.assertIn("#tag1#", keywords)
        self.assertIn("hello", html)

    def test_mark_text_v2_returns_MarkResult(self):
        msg = MessageDO()
        msg.content = "test content"
        msg.tag = "log"
        result = mark_text_v2(msg)
        self.assertIsInstance(result, MarkResult)
        self.assertIn("test", result.result_text)

    def test_heading_tag_filtering(self):
        heading_val = TagPrefixEnum.heading.value
        msg = MessageDO()
        msg.content = "# heading1\ncontent1\n# heading2\ncontent2"
        msg.tag = "log"
        msg.query_source = QuerySourceType.heading_tag
        msg.query_key = heading_val + "heading1"
        result = mark_text_v2(msg)
        self.assertIn("content1", result.result_text)
        self.assertNotIn("content2", result.result_text)

    def test_done_tag_uses_done_search(self):
        html, keywords = mark_text("task content", "done")
        self.assertIn("task", html)

    def test_keyword_set_returned(self):
        html, keywords = mark_text("#tag1# and #tag2#", "log")
        self.assertIn("#tag1#", keywords)
        self.assertIn("#tag2#", keywords)


class TestBuildSearchHtml(BaseTestCase):
    """测试 build_search_html 和 build_tag_html 函数"""

    def test_build_search_html(self):
        html = build_search_html("test_key", "log")
        self.assertIn("test_key", html)
        self.assertIn("href=", html)
        self.assertIn("tag=search", html)

    def test_build_tag_html_normal(self):
        tag_info = MsgTagInfo(tag_code="#test_tag#")
        tag_info.tag_name = "#test_tag#"
        tag_info.content = "#test_tag#"
        tag_info.is_sys_tag = False
        # Monkey-patch the property
        html = build_tag_html(tag_info, "log")
        self.assertIn("href=", html)
        self.assertIn("test_tag", html)


class TestMessageListParser(BaseTestCase):
    """测试 MessageListParser 类"""

    def test_prehandle_message_status_to_tag(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "test"
        msg.status = 0
        parser.prehandle_message(msg)
        self.assertEqual("task", msg.tag)

        msg2 = MessageDO()
        msg2.content = "test"
        msg2.status = 100
        parser.prehandle_message(msg2)
        self.assertEqual("done", msg2.tag)

    def test_prehandle_message_cron_to_task(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "test"
        msg.tag = "cron"
        parser.prehandle_message(msg)
        self.assertEqual("task", msg.tag)

    def test_prehandle_message_none_tag(self):
        parser = MessageListParser([], tag="log")
        msg = MessageDO()
        msg.content = "test"
        msg.tag = None
        parser.prehandle_message(msg)
        self.assertEqual("log", msg.tag)

    def test_process_message_empty_content(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = ""
        msg.tag = "log"
        result = parser.process_message(msg)
        self.assertIsNotNone(result)

    def test_process_message_sets_html_and_keywords(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "hello #tag1#"
        msg.tag = "log"
        result = parser.process_message(msg)
        self.assertIsNotNone(result.html)
        self.assertIsNotNone(result.keywords)
        self.assertIn("#tag1#", result.keywords)

    def test_process_message_system_tags(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "hello @user https://example.com"
        msg.tag = "log"
        result = parser.process_message(msg)
        self.assertIn(MessageTagEnum.people.value, result.system_tags)
        self.assertIn(MessageTagEnum.link.value, result.system_tags)

    def test_process_message_phone_system_tag(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "call 13800138000"
        msg.tag = "log"
        result = parser.process_message(msg)
        self.assertIn(MessageTagEnum.phone.value, result.system_tags)

    def test_process_message_book_system_tag(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "read 《三体》"
        msg.tag = "log"
        result = parser.process_message(msg)
        self.assertIn(MessageTagEnum.book.value, result.system_tags)

    def test_process_message_file_system_tag(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "file:///path/to/file"
        msg.tag = "log"
        result = parser.process_message(msg)
        self.assertIn(MessageTagEnum.file.value, result.system_tags)

    def test_process_message_keyword_html(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "#tag#"
        msg.tag = "log"
        result = parser.process_message(msg)
        self.assertIn("#tag#", result.keywords)

    def test_do_process_message_list(self):
        msg1 = MessageDO()
        msg1.content = "hello #tag1#"
        msg1.tag = "log"
        msg1.ctime = "2024-01-01 12:00:00"
        msg1.change_time = "2024-01-01 12:00:00"

        msg2 = MessageDO()
        msg2.content = "world #tag1# #tag2#"
        msg2.tag = "log"
        msg2.ctime = "2024-01-02 12:00:00"
        msg2.change_time = "2024-01-02 12:00:00"

        parser = MessageListParser([msg1, msg2])
        parser.do_process_message_list([msg1, msg2])
        keywords = parser.get_keywords()
        self.assertEqual(2, len(keywords))

    def test_get_system_tags_detection(self):
        parser = MessageListParser([])
        msg = MessageDO()
        msg.content = "@friend read 《book》 at https://example.com call 13800138000 file:///doc"
        msg.files = ["file.txt"]
        msg.tag = "log"
        result = parser.process_message(msg)
        for expected_tag in [
            MessageTagEnum.people.value,
            MessageTagEnum.link.value,
            MessageTagEnum.book.value,
            MessageTagEnum.phone.value,
            MessageTagEnum.file.value,
        ]:
            self.assertIn(expected_tag, result.system_tags)


class TestFilterMsgListByKey(BaseTestCase):
    """测试 filter_msg_list_by_key 和 filter_msg_list_by_keys 函数"""

    def make_msg(self, content, tag="log"):
        msg = MessageDO()
        msg.content = content
        msg.tag = tag
        return msg

    def test_filter_by_single_key(self):
        msg1 = self.make_msg("#tag1# hello")
        msg2 = self.make_msg("#tag2# world")
        msg3 = self.make_msg("plain")

        result = filter_msg_list_by_key([msg1, msg2, msg3], "#tag1#")
        self.assertEqual(1, len(result))

    def test_filter_by_no_tag(self):
        msg1 = self.make_msg("plain text")
        msg2 = self.make_msg("#tag1# hello")

        result = filter_msg_list_by_key([msg1, msg2], "$no_tag")
        self.assertEqual(1, len(result))
        # msg1 should match (no keywords initially, but process_message sets empty keywords)
        # After process_message, msg1.keywords will be set (empty set)

    def test_filter_by_multiple_keys_and(self):
        msg1 = self.make_msg("#tag1# #tag2# hello")
        msg2 = self.make_msg("#tag1# world")

        result = filter_msg_list_by_keys([msg1, msg2], ["#tag1#", "#tag2#"])
        self.assertEqual(1, len(result))

    def test_filter_by_multiple_keys_empty_result(self):
        msg1 = self.make_msg("#tag1# hello")
        msg2 = self.make_msg("#tag2# world")

        result = filter_msg_list_by_keys([msg1, msg2], ["#tag1#", "#tag2#"])
        self.assertEqual(0, len(result))

    def test_filter_by_multiple_keys_no_match(self):
        msg1 = self.make_msg("#tag3# hello")
        result = filter_msg_list_by_keys([msg1], ["#tag1#"])
        self.assertEqual(0, len(result))


class TestMessageKeyWordProcessor(BaseTestCase):
    """测试 MessageKeyWordProcessor 排序"""

    def make_tag_info(self, tag_code, amount=0, visit_cnt=0, mtime="", score=0.0):
        tag = MsgTagInfo(tag_code=tag_code)
        tag.content = tag_code
        tag.tag_name = tag_code
        tag.amount = amount
        tag.visit_cnt = visit_cnt
        tag.mtime = mtime
        tag.score = score
        return tag

    def test_sort_by_visit(self):
        tags = [
            self.make_tag_info("#a#", visit_cnt=5),
            self.make_tag_info("#b#", visit_cnt=10),
            self.make_tag_info("#c#", visit_cnt=1),
        ]
        processor = MessageKeyWordProcessor(tags)
        processor.sort("visit")
        self.assertEqual(10, tags[0].visit_cnt)
        self.assertEqual(5, tags[1].visit_cnt)
        self.assertEqual(1, tags[2].visit_cnt)

    def test_sort_by_amount_desc(self):
        tags = [
            self.make_tag_info("#a#", amount=5),
            self.make_tag_info("#b#", amount=10, score=1.0),
            self.make_tag_info("#c#", amount=1),
        ]
        processor = MessageKeyWordProcessor(tags)
        processor.sort("amount_desc")
        self.assertEqual("#b#", tags[0].content)

    def test_sort_by_recent(self):
        tags = [
            self.make_tag_info("#a#", mtime="2024-01-01"),
            self.make_tag_info("#b#", mtime="2024-06-01"),
            self.make_tag_info("#c#", mtime="2024-03-01"),
        ]
        processor = MessageKeyWordProcessor(tags)
        processor.sort("recent")
        self.assertEqual("2024-06-01", tags[0].mtime)
        self.assertEqual("2024-03-01", tags[1].mtime)

    def test_sort_empty_orderby_does_nothing(self):
        tags = [
            self.make_tag_info("#b#", amount=5),
            self.make_tag_info("#a#", amount=10),
        ]
        processor = MessageKeyWordProcessor(tags)
        processor.sort("")
        # order unchanged
        self.assertEqual("#b#", tags[0].content)


class TestFormatMessageStat(BaseTestCase):
    """测试 format_message_stat 函数"""

    def test_format_message_stat(self):
        stat = MessageStatDO(
            task_count=1500,
            done_count=300,
            log_count=50000,
            cron_count=100,
            search_count=2000000,
            key_count=999,
        )
        result = format_message_stat(stat)
        # NOTE: current implementation returns the original stat object, not the VO
        self.assertIsInstance(result, MessageStatDO)


class TestCountMonthSize(BaseTestCase):
    """测试 count_month_size 函数"""

    def test_count_empty(self):
        self.assertEqual(0, count_month_size([]))

    def test_count_non_empty(self):
        f1 = MessageFolder()
        f1.item_list = [1, 2]
        f2 = MessageFolder()
        f2.item_list = [3]
        self.assertEqual(3, count_month_size([f1, f2]))


class TestConvertMessageListToDayFolder(BaseTestCase):
    """测试 convert_message_list_to_day_folder 函数"""

    def test_empty_list(self):
        result = convert_message_list_to_day_folder([], "2024-01")
        self.assertEqual(0, len(result))

    def test_with_messages(self):
        msg = MessageDO()
        msg.content = "test"
        msg.tag = "log"
        msg.ctime = "2024-01-15 12:00:00"
        msg.change_time = "2024-01-15 12:00:00"

        result = convert_message_list_to_day_folder([msg], "2024-01")
        self.assertGreater(len(result), 0)
        # find the folder containing our message
        found = False
        for folder in result:
            if len(folder.item_list) > 0:
                self.assertEqual(msg.content, folder.item_list[0].content)
                found = True
        self.assertTrue(found)


class TestGetTagsFromMessageList(BaseTestCase):
    """测试 get_tags_from_message_list 函数"""

    def test_empty_list(self):
        result = get_tags_from_message_list([], input_tag="log")
        self.assertEqual([], result)

    def test_with_messages_having_tags(self):
        msg = MessageDO()
        msg.content = "#tag1# #tag2# hello"
        msg.tag = "log"
        msg.ctime = "2024-01-15 12:00:00"
        msg.mtime = "2024-01-15 12:00:00"
        msg.change_time = "2024-01-15 12:00:00"

        result = get_tags_from_message_list([msg], input_tag="log")
        self.assertGreater(len(result), 0)
        tag_names = [t.tag_name for t in result]
        self.assertIn("#tag1#", tag_names)
        self.assertIn("#tag2#", tag_names)

    def test_no_tag_message(self):
        msg = MessageDO()
        msg.content = "plain text without tags"
        msg.tag = "log"
        msg.ctime = "2024-01-15 12:00:00"
        msg.mtime = "2024-01-15 12:00:00"
        msg.change_time = "2024-01-15 12:00:00"

        result = get_tags_from_message_list([msg], input_tag="log")
        tag_names = [t.tag_name for t in result]
        self.assertIn("<无标签>", tag_names)

    def test_sort_by_amount(self):
        msg1 = MessageDO()
        msg1.content = "#common# hello"
        msg1.tag = "log"
        msg1.ctime = "2024-01-15 12:00:00"
        msg1.mtime = "2024-01-15 12:00:00"
        msg1.change_time = "2024-01-15 12:00:00"

        msg2 = MessageDO()
        msg2.content = "#common# #rare# world"
        msg2.tag = "log"
        msg2.ctime = "2024-01-16 12:00:00"
        msg2.mtime = "2024-01-16 12:00:00"
        msg2.change_time = "2024-01-16 12:00:00"

        result = get_tags_from_message_list([msg1, msg2], input_tag="log")
        self.assertEqual(2, len(result))
        self.assertEqual("#common#", result[0].tag_name)
