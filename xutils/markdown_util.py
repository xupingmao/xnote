

def has_latex(content: str):
    if "```latex" in content:
        return True
    if "\\(" in content and "\\)" in content:
        return True
    return False