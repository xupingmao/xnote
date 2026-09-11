# -*- coding:utf-8 -*-
"""机器人的回复规则引擎(机器人专用层)

- 规则按 priority 倒序排列, 首个命中的规则产生回复
- 通过 register_rule 注册自定义规则, 也可以通过继承 BaseRule 实现复杂规则
"""

from typing import Callable, List, Optional

from xutils import dateutil
from xutils import textutil
from xutils.base import BaseDataRecord


class ReplyContext(BaseDataRecord):
    """规则匹配的输入"""

    def __init__(self):
        self.user_id: int = 0
        self.user_name: str = ""
        self.session_id: int = 0
        self.content: str = ""
        # 去掉触发词后剩余的内容, 供 echo 之类的规则使用
        self.keyword: str = ""


class ReplyResult(BaseDataRecord):
    """规则匹配的产出"""

    def __init__(self):
        self.content: str = ""
        self.rule_name: str = ""


class MatchMode:
    """关键词匹配模式"""
    contains = "contains"
    prefix = "prefix"
    exact = "exact"


class BaseRule:
    """规则基类"""

    name = ""
    priority = 0

    def match(self, ctx: ReplyContext) -> bool:
        raise NotImplementedError()

    def handle(self, ctx: ReplyContext) -> str:
        raise NotImplementedError()


class KeywordRule(BaseRule):
    """关键词匹配规则

    reply 与 handler 二选一:
    - reply: 静态回复文本, 支持 {user_name} 和 {content} 占位符
    - handler: 动态回复, 入参是 ReplyContext, 返回回复文本
    """

    def __init__(self, name: str = "", keywords: List[str] = [],
                 reply: str = "",
                 handler: Optional[Callable[[ReplyContext], str]] = None,
                 match_mode: str = MatchMode.contains, priority: int = 0,
                 strip_keyword: bool = True):
        self.name = name
        self.keywords = keywords
        self.reply = reply
        self.handler = handler
        self.match_mode = match_mode
        self.priority = priority
        self.strip_keyword = strip_keyword

    def find_keyword(self, content: str) -> str:
        """返回命中的关键词, 没有命中返回空字符串"""
        lowered = content.lower()
        for keyword in self.keywords:
            target = keyword.lower()
            if self.match_mode == MatchMode.exact:
                if lowered == target:
                    return keyword
            elif self.match_mode == MatchMode.prefix:
                if lowered.startswith(target):
                    return keyword
            else:
                if target in lowered:
                    return keyword
        return ""

    def match(self, ctx: ReplyContext) -> bool:
        return self.find_keyword(ctx.content) != ""

    def handle(self, ctx: ReplyContext) -> str:
        keyword = self.find_keyword(ctx.content)
        ctx.keyword = self.build_keyword(ctx.content, keyword)

        if self.handler is not None:
            return self.handler(ctx)
        return self.format_reply(ctx)

    def build_keyword(self, content: str, keyword: str) -> str:
        """从原始内容中剔除触发词, 保留原始大小写"""
        if not self.strip_keyword or keyword == "":
            return content

        if self.match_mode == MatchMode.prefix:
            return content[len(keyword):].strip()

        index = content.lower().find(keyword.lower())
        if index < 0:
            return content
        return (content[:index] + content[index + len(keyword):]).strip()

    def format_reply(self, ctx: ReplyContext) -> str:
        result = self.reply
        result = result.replace("{user_name}", ctx.user_name)
        result = result.replace("{content}", ctx.content)
        return result


_rules: List[BaseRule] = []

FALLBACK_TEMPLATE = "抱歉，我还不懂「{content}」的意思。输入 help 或 帮助 看看我能做什么~"

HELP_CONTENT = """我可以帮你做这些事:
1. 报时间 - 试试输入「时间」或者「今天」
2. 复读 - 试试输入「复读 你好」
3. 查身份 - 试试输入「我是谁」
输入「help」可以随时看到这条说明。"""


def register_rule(rule: BaseRule) -> None:
    """注册规则, 按 priority 倒序排列(priority 大的先匹配)"""
    _rules.append(rule)
    _rules.sort(key=lambda item: item.priority, reverse=True)


def get_rules() -> List[BaseRule]:
    return _rules


def build_context(user_id: int = 0, user_name: str = "", session_id: int = 0,
                  content: str = "") -> ReplyContext:
    ctx = ReplyContext()
    ctx.user_id = user_id
    ctx.user_name = user_name
    ctx.session_id = session_id
    ctx.content = content
    return ctx


def build_fallback_result(ctx: ReplyContext) -> ReplyResult:
    result = ReplyResult()
    result.rule_name = "fallback"
    result.content = FALLBACK_TEMPLATE.replace(
        "{content}", textutil.get_short_text(ctx.content, 20))
    return result


def reply(ctx: ReplyContext) -> ReplyResult:
    """按规则顺序匹配, 返回首个命中的回复"""
    for rule in _rules:
        if rule.match(ctx):
            result = ReplyResult()
            result.rule_name = rule.name
            result.content = rule.handle(ctx)
            return result
    return build_fallback_result(ctx)


def handle_time_rule(ctx: ReplyContext) -> str:
    return "现在是 " + dateutil.format_datetime()


def handle_echo_rule(ctx: ReplyContext) -> str:
    if ctx.keyword == "":
        return "你想让我复读什么呢？"
    return ctx.keyword


def handle_whoami_rule(ctx: ReplyContext) -> str:
    return "你是 " + ctx.user_name


def register_default_rules() -> None:
    """注册内置的默认规则"""
    register_rule(KeywordRule(
        name="greeting",
        keywords=["你好", "hello", "hi", "在吗"],
        reply="你好，{user_name}！有什么可以帮你的吗？输入 help 看看我能做什么~",
        priority=10,
    ))
    register_rule(KeywordRule(
        name="help",
        keywords=["help", "帮助", "?", "？", "菜单"],
        reply=HELP_CONTENT,
    ))
    register_rule(KeywordRule(
        name="time",
        keywords=["时间", "几点", "日期", "今天", "time", "date"],
        handler=handle_time_rule,
    ))
    register_rule(KeywordRule(
        name="echo",
        keywords=["echo ", "复读 "],
        handler=handle_echo_rule,
        match_mode=MatchMode.prefix,
        # 前缀匹配比 contains 更具体, 优先级要高于 greeting 等 contains 规则,
        # 否则 "复读 hello" 会被 greeting 的 "hello" 先截胡
        priority=20,
    ))
    register_rule(KeywordRule(
        name="whoami",
        keywords=["我是谁", "whoami", "我的名字"],
        handler=handle_whoami_rule,
    ))


register_default_rules()
