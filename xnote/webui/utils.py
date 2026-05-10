from typing import Optional
from xutils import escape_html

def build_data_attrs(dict_: Optional[dict]):
    if dict_ is None:
        return ""
    items = [f'data-{key}="{escape_html(value)}"' for key, value in dict_.items()]
    return " ".join(items)

def build_attrs(dict_: Optional[dict]):
    if dict_ is None:
        return ""
    items = [f'{key}="{escape_html(value)}"' for key, value in dict_.items()]
    return " ".join(items)