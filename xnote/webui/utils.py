from typing import Optional
from xutils import escape_html

def build_data_attrs(dict_: Optional[dict]):
    if dict_ is None:
        return ""
    items = [f'data-{key}="{escape_html(value)}"' for key, value in dict_.items()]
    return " ".join(items)

def build_attrs(dict_: Optional[dict], ignore_empty = True):
    if dict_ is None:
        return ""

    if ignore_empty:
        items = [f'{key}="{escape_html(value)}"' for key, value in dict_.items() if value]
    else:
        items = [f'{key}="{escape_html(value)}"' for key, value in dict_.items()]
    return " ".join(items)

def get_first_valid_arg(*args):
    """获取第一个非None的参数
    用于处理参数别名, 旧名称在前面, 新名称放在后面, 比如 get_first_valid_arg(old_arg, new_arg)
    定义别名的时候, 新的参数可以设置默认值, 旧的参数必须默认为None
    """
    if len(args) == 0:
        return None
    for arg in args:
        if arg is not None:
            return arg
    return None
