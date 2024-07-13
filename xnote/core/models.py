# encoding=utf-8


class SearchContext:
    def __init__(self, key=""):
        # 输入的文本
        self.key = key
        self.input_text = key
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