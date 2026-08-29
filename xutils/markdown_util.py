try:
    import markdown
except ImportError:
    markdown = None

import re

from xutils.text_parser import TextParser

# 块级 $$...$$ 公式（可跨行）
_LATEX_BLOCK_DOLLAR_RE = re.compile(r"(?<!\\)\$\$[\s\S]+?\$\$")

# 行内 $...$ 公式（单行、内容不含 $ 与换行）
_LATEX_INLINE_DOLLAR_RE = re.compile(r"(?<!\\)\$[^$\n]+?(?<!\\)\$")

def has_latex(content: str):
    """检测文本中是否含有latex公式"""
    if "```latex" in content:
        return True
    if "\\(" in content and "\\)" in content:
        return True
    if "\\[" in content and "\\]" in content:
        return True
    # 块级/行内 $...$ / $$...$$ 公式
    if _LATEX_BLOCK_DOLLAR_RE.search(content):
        return True
    if _LATEX_INLINE_DOLLAR_RE.search(content):
        return True
    return False

def has_mermaid(content: str):
    """检测文本中是否含有mermaid图表"""
    if "```mermaid" in content:
        return True
    return False

def render_html(text: str) -> str:
    if markdown:
        return markdown.markdown(text)

    parser = TextParser()
    return parser.render_html(text)
