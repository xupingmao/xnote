try:
    import markdown
except ImportError:
    markdown = None

from xutils.text_parser import TextParser

def has_latex(content: str):
    """检测文本中是否含有latex公式"""
    if "```latex" in content:
        return True
    if "\\(" in content and "\\)" in content:
        return True
    if "\\[" in content and "\\]" in content:
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
