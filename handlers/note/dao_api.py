# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-11-19 15:16:04
@LastEditors  : xupingmao
@LastEditTime : 2022-12-10 21:48:07
@FilePath     : /xnote/handlers/note/dao_api.py
@Description  : 接口定义
"""

class NoteDao:

    @staticmethod
    def get_by_id(id, include_full=True, creator=None):
        """通过ID查询笔记信息"""
        raise NotImplementedError()
    
    @staticmethod
    def batch_query_list(id_list):
        """通过ID列表批量查询笔记"""
        raise NotImplementedError()

    @staticmethod
    def count_tag(user_name):
        # type: (str)->int
        """统计标签数量"""
        raise NotImplementedError()
    
    @staticmethod
    def count_comment(user_name):
        # type: (str)->int
        """统计评论数量"""
        raise NotImplementedError()
    
    @staticmethod
    def delete_visit_log(user_name, note_id):
        # type: (str, str) -> None
        """删除访问日志"""
        raise NotImplementedError()
    
    @staticmethod
    def delete_note(id):
        # type: (str) -> None
        """删除笔记"""
        raise NotImplementedError()

    @staticmethod
    def update_content(note, new_content, clear_draft = True):
        # type: (dict, str, bool) -> None
        """更新笔记内容"""
        raise NotImplementedError()
    
    @staticmethod
    def add_history(note_id, version, new_note):
        """保存笔记修改历史"""
        raise NotImplementedError()
    
    @staticmethod
    def get_root(creator=None):
        raise NotImplementedError()