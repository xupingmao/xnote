# encoding=utf-8

from xutils import SearchResult

class SearchOption:
    def __init__(self) -> None:
        self.show_message_detail = False

class SearchContext:
    def __init__(self, key=""):
        # 输入的文本
        self.key = key
        self.input_text = key
        self.words = [] # 根据key分割的token
        self.category = "" # 搜索类型

        # 搜索选项
        self.option = SearchOption()

        # 正则匹配的分组
        self.groups           = []
        self.user_name        = ""
        self.user_id = 0
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
        self.commands = [] # type: list[SearchResult] # 命令
        self.tools    = [] # type: list[SearchResult] # 工具
        self.dicts    = [] # type: list[SearchResult] # 词典 -- 公共
        self.messages = [] # type: list[SearchResult] # 待办/记事/通知/评论
        self.notes    = [] # type: list[SearchResult] # 笔记
        self.files    = [] # type: list[SearchResult] # 文件
        self.parent_note = None # type: object # 上级笔记

        # 分页信息
        self.offset = 1
        self.limit = 20

    def join_as_files(self):
        return self.commands + self.tools + self.dicts + self.messages + self.notes + self.files
