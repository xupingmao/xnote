# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/11/19 00:05:56
# @modified 2026/09/06 00:00:00

"""A small Python-source tokenizer (lexical analyzer).

It is good enough to consume every character of real Python source code
without raising, which makes it usable as a lightweight "syntax parsing"
check. It is NOT a full Python parser: it does not build an AST and some
tokens (e.g. multi-character operators) are emitted as separate single
character tokens.
"""

import typing
from typing import Any
from typing import List
from typing import Optional


class TokenTypeEnum:
    symbol = "symbol"


class Token:
    """A single lexical token."""

    def __init__(self, type: Optional[str] = "symbol", val: Any = None,
                 line: Optional[int] = None, col: Optional[int] = None) -> None:
        self.line = line
        self.col = col
        self.type = type
        self.val = val

    def before(self) -> Optional["Token"]:
        if self.type is None:
            return _empty_token
        return None

    def after(self) -> Optional["Token"]:
        if self.type is None:
            return _empty_token
        return None

    def __str__(self) -> str:
        return str(self.__dict__)


# sentinel token returned by Token.before()/after() for empty tokens
_empty_token = Token(None, None, -1, -1)


def findpos(token: Any) -> List[int]:
    """Find the [line, col] source position of a token.

    Falls back to the ``first`` attribute (for tree nodes) or [0, 0].
    """
    if not hasattr(token, 'line'):
        if hasattr(token, "first"):
            return findpos(token.first)
        print(token)
        return [0, 0]
    return [token.line, token.col]


def find_error_line(s: str, pos: List[int]) -> str:
    """Build a readable error line pointing at `pos`."""
    y = pos[0]
    x = pos[1]
    s = s.replace('\t', ' ')
    line = s.split('\n')[y - 1]
    p = ''
    if y < 10:
        p += ' '
    if y < 100:
        p += '  '
    r = p + str(y) + ": " + line + "\n"
    r += "     " + " " * x + "^" + '\n'
    return r


def report_error(ctx: str, s: str, token: Any, e_msg: str = "") -> None:
    """Raise an Exception with source location information."""
    if token is not None:
        pos = findpos(token)
        r = find_error_line(s, pos)
        raise Exception('Error at ' + ctx + ':\n' + r + e_msg)
    else:
        raise Exception(e_msg)


# characters that start a symbol token
_ISYMBOLS = '-=[];,./!%*()+{}:<>@^&|~'

KEYWORDS = [
    'as', 'def', 'class', 'return', 'pass', 'and', 'or', 'not', 'in', 'import',
    'is', 'while', 'break', 'for', 'continue', 'if', 'else', 'elif', 'try',
    'except', 'raise', 'global', 'del', 'from', 'None', "assert",
]

# ordered longest-first so multi-char operators match before single chars
SYMBOLS = [
    '-=', '+=', '*=', '/=', '==', '!=', '<=', '>=',
    '=', '-', '+', '*', '/', '%',
    '<', '>',
    '[', ']', '{', '}', '(', ')', '.', ':', ',', ';',
    '^', '&', '|', '~', '@',
]

_B_BEGIN = ['[', '(', '{']
_END = [']', ')', '}']


class TokenizeContext:
    """Mutable state of the tokenizer while scanning one source string."""

    def __init__(self) -> None:
        self.text = ""         # source string being tokenized
        self.length = 0        # len(self.text)
        self.line = 1          # current line number (1-based)
        self.line_start = 0    # index of the start of the current line
        self.col = 1           # current column number (1-based)
        self.nl = True         # True when the scanner is at the start of a line
        self.res = []  # type: List[Token]  # list of Token produced so far
        self.indent = [0]      # indent width stack
        self.braces = 0        # current brace depth

    def add(self, t: str, v: Any) -> None:
        """Append a token, merging `not in` -> `notin` and `is not` -> `isnot`."""
        if t == 'in':
            last = self.res.pop()
            if last.type == 'not':
                self.res.append(Token('notin', v, self.line, self.col))
            else:
                self.res.append(last)
                self.res.append(Token(t, v, self.line, self.col))
        elif t == 'not':
            # is not
            last = self.res.pop()
            if last.type == 'is':
                self.res.append(Token("isnot", v, self.line, self.col))
            else:
                self.res.append(last)
                self.res.append(Token(t, v, self.line, self.col))
        else:
            self.res.append(Token(t, v, self.line, self.col))


def clean(s: str) -> str:
    # strip UTF-8 BOM so files saved with a BOM still tokenize
    s = s.replace('\ufeff', '')
    s = s.replace('\r', '')
    return s


def tokenize(s: str) -> List[Token]:
    s = clean(s)
    ctx = TokenizeContext()
    ctx.text = s
    ctx.length = len(s)
    return do_tokenize(ctx)


def do_tokenize(ctx: TokenizeContext) -> List[Token]:
    i = 0
    s = ctx.text
    l = ctx.length
    while i < l:
        c = s[i]
        ctx.col = i - ctx.line_start + 1
        if ctx.nl:
            ctx.nl = False
            i = do_indent(ctx, i)
        elif c == '\n':
            i = do_nl(ctx, i)
        elif c in _ISYMBOLS:
            i = do_symbol(ctx, i)
        elif c >= '0' and c <= '9':
            i = do_number(ctx, i)
        elif is_name_begin(c):
            i = do_name(ctx, i)
        elif c == '"' or c == "'":
            i = do_string(ctx, i)
        elif c == '#':
            i = do_comment(ctx, i)
        elif c == '\\' and s[i + 1] == '\n':
            i += 2
            ctx.line += 1
            ctx.line_start = i
        elif c == ' ' or c == '\t':
            i += 1
        else:
            report_error('do_tokenize', s, Token('', '', ctx.line, ctx.col), "unknown token")
    indent(ctx, 0)
    return ctx.res


def do_nl(ctx: TokenizeContext, i: int) -> int:
    if not ctx.braces:
        ctx.add('nl', 'nl')
    i += 1
    ctx.nl = True
    ctx.line += 1
    ctx.line_start = i
    return i


def do_indent(ctx: TokenizeContext, i: int) -> int:
    s = ctx.text
    l = ctx.length
    v = 0
    c = ''  # type: str
    while i < l:
        c = s[i]
        if c != ' ' and c != '\t':
            break
        i += 1
        v += 1
    # skip blank line or comment line.
    # i >= l means reaching EOF, which does not need to indent or dedent
    if not ctx.braces and c != '\n' and c != '#' and i < l:
        indent(ctx, v)
    return i


def indent(ctx: TokenizeContext, v: int) -> None:
    if v == ctx.indent[-1]:
        pass
    elif v > ctx.indent[-1]:
        ctx.indent.append(v)
        ctx.add('indent', v)
    elif v < ctx.indent[-1]:
        n = ctx.indent.index(v)
        while len(ctx.indent) > n + 1:
            v = ctx.indent.pop()
            ctx.add('dedent', v)


def do_symbol(ctx: TokenizeContext, i: int) -> int:
    s = ctx.text
    v = None  # type: Optional[str]
    for sb in SYMBOLS:
        if s.startswith(sb, i):
            i += len(sb)
            v = sb
            break
    if v is None:
        raise Exception("invalid symbol")
    ctx.add(v, v)
    if v in _B_BEGIN:
        ctx.braces += 1
    if v in _END:
        ctx.braces -= 1
    return i


def do_number(ctx: TokenizeContext, i: int) -> int:
    s = ctx.text
    l = ctx.length
    v = s[i]
    i += 1
    c = None  # type: Optional[str]
    while i < l:
        c = s[i]
        if (c < '0' or c > '9') and (c < 'a' or c > 'f') and c != 'x':
            break
        v += c
        i += 1
    if c == '.':
        v += c
        i += 1
        while i < l:
            c = s[i]
            if c < '0' or c > '9':
                break
            v += c
            i += 1
    # accept decimal floats, plus hex/bin/oct literals when present
    value = _parse_number_literal(v)
    ctx.add('number', value)
    return i


def _parse_number_literal(v: str) -> Any:
    try:
        return float(v)
    except ValueError:
        try:
            return int(v, 0)
        except ValueError:
            return v


def is_name_begin(c: str) -> bool:
    return (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z') or (c in '_$')


def is_name(c: str) -> bool:
    return (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z') \
        or (c in '_$') or (c >= '0' and c <= '9')


def do_name(ctx: TokenizeContext, i: int) -> int:
    s = ctx.text
    l = ctx.length
    v = s[i]
    i += 1
    while i < l:
        c = s[i]
        if not is_name(c):
            break
        v += c
        i += 1
    if v in KEYWORDS:
        ctx.add(v, v)
    else:
        ctx.add('name', v)
    return i


def do_string(ctx: TokenizeContext, i: int) -> int:
    s = ctx.text
    l = ctx.length
    v = ''
    q = s[i]
    i += 1
    if (l - i) >= 5 and s[i] == q and s[i + 1] == q:  # """
        i += 2
        while i < l - 2:
            c = s[i]
            if c == q and s[i + 1] == q and s[i + 2] == q:
                i += 3
                ctx.add('string', v)
                break
            else:
                v += c
                i += 1
                if c == '\n':
                    ctx.line += 1
    else:
        while i < l:
            c = s[i]
            if c == "\\":
                i = i + 1
                c = s[i]
                if c == "n":
                    c = '\n'
                elif c == "r":
                    c = chr(13)
                elif c == "t":
                    c = "\t"
                elif c == "0":
                    c = "\0"
                elif c == 'b':
                    c = '\b'
                v += c
                i += 1
            elif c == q:
                i += 1
                ctx.add('string', v)
                break
            else:
                v += c
                i += 1
    return i


def do_comment(ctx: TokenizeContext, i: int) -> int:
    s = ctx.text
    l = ctx.length
    i += 1
    value = ""
    while i < l:
        if s[i] == '\n':
            break
        value += s[i]
        i += 1
    if value.startswith("@debugger"):
        ctx.add("@", "debugger")
    return i


def loadfile(fname: str) -> str:
    with open(fname, encoding="utf-8") as fp:
        return fp.read()


def main_test() -> None:
    import sys
    ARGV = sys.argv
    if len(ARGV) == 1:
        content = '''
        this is a example
        a = 10
        c = 'a string'
        float = 1.2
        '''
    elif len(ARGV) == 2:
        fname = ARGV[1]
        print("try to tokenize file ", fname)
        content = loadfile(fname)
    else:
        print("Usage: %s [filename]" % sys.argv[0])
        return

    tokens = tokenize(content)
    fmt = "%-6s %-8s %-12s %s"
    print(fmt % ("index", "type", "pos", "val"))
    print(fmt % ("-"*6, "-"*8, "-"*12, "-" * 6))
    for index, token in enumerate(tokens):
        print(fmt % (index + 1, token.type, [token.line, token.col], repr(token.val)))


if __name__ == "__main__":
    main_test()
