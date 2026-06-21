
import typing
import time

from typing import List, Sequence, Tuple
from .models import NoteIndexDO, OrderTypeEnum
from xnote.core import xauth
from .dao_index import NoteIndexDao, NoteIndexDO, NoteDO
from .dao_index import build_note_info, build_note_list_info
from xnote.core.models import SearchResult
from xutils import htmlutil, textutil, dateutil
from xnote.webui import TagSpan, TextTag
from .dao_base import _full_db, sort_notes, sort_by_priority, fill_parent_name
from xnote.service.search_service import SearchHistoryDO, SearchHistoryService, SearchHistoryType
from xnote.webui import RowPanel

MAX_SEARCH_SIZE = 1000
MAX_SEARCH_KEY_LENGTH = 20

class NoteSearchSorter:
    def __init__(self, words: Sequence[str]):
        self.search_key = " ".join(words).lower()
    
    def key(self, note: NoteIndexDO) -> Tuple[int,int,int]:
        if note.name.lower() == self.search_key:
            name_score = 0
        else:
            name_score = 1
        
        priority_score = 0
        if note.is_pinned:
            priority_score = 0
        else:
            priority_score = 1
        
        hot_index_score = -note.hot_index
        return (priority_score, name_score, hot_index_score)

def search_name(words: List[str], creator="", creator_id = 0, parent_id=0, limit=1000, 
                exclude_types=[], type_list=[]):
    # TODO 搜索排序使用索引
    assert isinstance(words, list)

    words = [word.lower() for word in words]
    name_like = ""
    if len(words) > 0:
        name_like = "%" + "%".join(words) + "%"
    
    if creator_id == 0:
        creator_id = xauth.UserDao.get_id_by_name(creator)

    result = NoteIndexDao.list(creator_id=creator_id, parent_id=parent_id, limit=limit, 
                               name_like=name_like, exclude_types=exclude_types, type_list=type_list)

    # 补全信息
    build_note_list_info(result, order_type=OrderTypeEnum.hot.int_value)

    # 对笔记进行排序
    sorter = NoteSearchSorter(words)
    result.sort(key = sorter.key)
    return result

def search_short_desc(words: typing.List[str], creator_id = 0, parent_id=0, orderby="hot_index", limit=1000, 
                exclude_types=[], type_list=[]):
    words = [word.lower() for word in words]

    name_like = ""
    if len(words) > 0:
        name_like = "%" + "%".join(words) + "%"

    result = NoteIndexDao.list(creator_id=creator_id, parent_id=parent_id, limit=limit,
                               short_desc_like=name_like, exclude_types=exclude_types, type_list=type_list)

    # 补全信息
    build_note_list_info(result, order_type=OrderTypeEnum.hot.int_value)

    # 对笔记进行排序
    sort_notes(result, orderby)
    sort_by_priority(result)
    return result

def search_content(words: List[str], creator_id: int, limit=1000):
    # TODO 全文搜索排序使用索引
    assert isinstance(words, list)
    words = [word.lower() for word in words]

    def is_match(value: NoteDO):
        if value.content is None:
            return False
        return (value.creator_id == creator_id or value.is_public) \
            and textutil.contains_all(value.content.lower(), words)

    result: List[NoteDO] = []

    for index_list in NoteIndexDao.iter_batch(creator_id=creator_id, batch_size=20):
        id_list = [str(x.id) for x in index_list]
        batch_result = _full_db.batch_get_by_id(id_list)
        for key in batch_result:
            value = NoteDO.from_dict(batch_result[key])
            if is_match(value):
                value.content = ""
                value.data = ""
                result.append(value)
            if len(result) > limit:
                break

    # 补全信息
    build_note_list_info(result)

    sorter = NoteSearchSorter(words)
    result.sort(key = sorter.key)
    return result


def search_public(words):
    assert isinstance(words, list)
    words = [word.lower() for word in words]

    def search_public_func(key, value):
        if value.content is None:
            return False
        if not value.is_public:
            return False
        return textutil.contains_all(value.name.lower(), words)
    result = _full_db.list(filter_func=search_public_func,
                           offset=0, limit=MAX_SEARCH_SIZE)
    notes = [build_note_info(item) for item in result]
    sort_notes(notes)
    return notes

def search_group(words: typing.List[str], creator_id=0, parent_id=0) -> typing.List[SearchResult]:
    groups = search_name(words, creator_id = creator_id, parent_id = parent_id, type_list=["group"])
    if len(groups) == 0:
        return []
    
    result = SearchResult()
    result.name = f"搜索到{len(groups)}个笔记本"
    result.icon = "fa fa-folder"

    html = ""
    for group in groups:
        name_html = htmlutil.highlight(group.name, words)
        html += TagSpan(text_html=name_html, href=group.url).render()
    result.html = html
    return [result]


def add_search_history(user, search_key: str, category="default", cost_time=0.0):
    if user == None:
        user_id = 0
    else:
        user_id = xauth.UserDao.get_id_by_name(user)
    
    if len(search_key) > MAX_SEARCH_KEY_LENGTH:
        return
    
    expire_search_history(user)
    
    value = SearchHistoryDO()
    value.user_id = user_id
    value.search_key = search_key
    value.search_type = category
    value.cost_time_ms = int(cost_time)

    return SearchHistoryService.create(value)


def list_search_history(user, limit=1000, search_type=SearchHistoryType.default, orderby="ctime desc") -> typing.List[SearchHistoryDO]:
    if user is None or user == "":
        return []
    
    user_id = xauth.UserDao.get_id_by_name(user)
    result = []
    for value in SearchHistoryService.list(user_id=user_id, search_type=search_type, limit = limit, order=orderby):
        result.append(value)
    
    result.sort(key = lambda x:x.ctime, reverse = True)
    return result


def clear_search_history(user_name, search_type=""):
    assert user_name != None
    assert user_name != ""
    user_id = xauth.UserDao.get_id_by_name(user_name)

    ids = []
    for item in SearchHistoryService.list(user_id=user_id, search_type=search_type, limit=1000, order="ctime asc"):
        ids.append(item.id)
    SearchHistoryService.delete_by_ids(ids)

def expire_search_history(user_name, limit=1000, search_type=SearchHistoryType.default):
    db = SearchHistoryService
    user_id = xauth.UserDao.get_id_by_name(user_name)
    count = db.count(user_id=user_id, search_type=search_type)
    delete_limit = 20
    if count > limit + delete_limit:
        obj_list = db.list(user_id=user_id, search_type=search_type, limit = delete_limit, order="ctime asc")
        db.delete_items(obj_list)
        

def merge_notes(a: List[NoteIndexDO], b: List[NoteIndexDO],  words=[], orderby="hot_index"):
    idset = set()
    result:List[NoteIndexDO] = []
    for item in a:
        idset.add(item.note_id)
        result.append(item)
    
    for item in b:
        if item.note_id in idset:
            continue
        result.append(item)
    
    sorter = NoteSearchSorter(words)
    result.sort(key = sorter.key)
    return result

def to_search_results(notes: Sequence[NoteIndexDO], words: List[str]) -> typing.List[SearchResult]:
    fill_parent_name(notes)
    
    result:List[SearchResult] = []
    for note in notes:
        item = SearchResult()
        item.id = note.note_id
        item.name = note.name
        item.url = note.url
        item.icon = note.icon
        item.show_move = True
        item.parent_id = note.parent_id
        item.creator = note.creator
        item.badge_info = note.badge_info
        item.name_html = htmlutil.highlight(note.name, words)
        item.short_desc = htmlutil.highlight(note.manual_short_desc, words)
        item.html = build_note_extra_html(note)
        result.append(item)
    return result

def build_note_extra_html(note: NoteIndexDO):
    result = RowPanel(css_class="margin-top-sm")
    if note.is_pinned:
        result.add(TextTag(text="置顶", css_class="orange-tag"))
    if note.is_public:
        result.add(TextTag(text="公开", css_class="green-tag"))
    if note.creator:
        result.add(TextTag(text=note.creator, css_class="lightgray"))
    if note.parent_name:
        result.add(TextTag(text=note.parent_name, css_class="lightgray", href=note.url))
    result.extra.add_span(note.badge_info, css_class="search-badge-info")
    return result.render()