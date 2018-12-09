# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/11/19 00:05:56
# @modified 2018/12/09 15:40:36

class Token:

    def __init__(self,type='symbol',val=None,pos=None):
        self.pos=pos
        self.type=type
        self.val=val

    def before(self):
        if self.type == None:
            return _empty_token

    def after(self):
        if self.type == None:
            return _empty_token

    def __str__(self):
        return str(self.__dict__)

_empty_token = Token(None, None, [-1,-1])

def findpos(token):
    if not hasattr(token, 'pos'):
        if hasattr(token, "first"):
            return findpos(token.first)
        print(token)
        return [0,0]
    return token.pos


def find_error_line(s, pos):
    """找到错误行
    @param {string} s 源代码
    @param {list} pos 位置
        print("****************")
        print(pos, pos.type, pos.val, pos.pos)
    """
    y = pos[0]
    x = pos[1]
    s = s.replace('\t', ' ')
    line = s.split('\n')[y-1]
    p = ''
    if y < 10: p += ' '
    if y < 100: p += '  '
    r = p + str(y) + ": " + line + "\n"
    r += "     "+" "*x+"^" +'\n'
    return r

def print_token(token):
    for key in token:
        print(key, token[key])
        if gettype(token[key]) == "dict":
            print_token(token[key])
    
def report_error(ctx, s, token, e_msg = ""):
    if token != None:
        # print_token(token)
        pos = findpos(token)
        r = find_error_line(s, pos)
        raise Exception('Error at '+ctx+':\n'+r + e_msg)
    else:
        raise Exception(e_msg)
    #raise

_ISYMBOLS = '-=[];,./!%*()+{}:<>@^'
KEYWORDS = [
    'as','def','class', 'return','pass','and','or','not','in','import',
    'is','while','break','for','continue','if','else','elif','try',
    'except','raise','global','del','from','None', "assert"]

SYMBOLS = [
    '-=','+=','*=','/=','==','!=','<=','>=',
    '=','-','+','*', '/', '%',
    '<','>',
    '[',']','{','}','(',')','.',':',',',';',
]
_B_BEGIN = ['[','(','{']
_END = [']',')','}']

class TData:
    def __init__(self):
        self.y=1
        self.yi=0
        self.nl=True
        self.res=[]
        self.indent=[0]
        self.braces=0

    def add(self,t,v): 
        if t == 'in':
            last = self.res.pop()
            if last.type == 'not':
                self.res.append(Token('notin', v, self.f))
            else:
                self.res.append(last)
                self.res.append(Token(t,v,self.f))
        elif t == 'not':
            # is not
            last = self.res.pop()
            if last.type == 'is':
                self.res.append(Token("isnot", v, self.f))
            else:
                self.res.append(last)
                self.res.append(Token(t,v,self.f))
        else:
            self.res.append(Token(t,v,self.f))

def clean(s):
    s = s.replace('\r','')
    return s

def tokenize(s):
    global T
    s = clean(s)
    return do_tokenize(s)
        
def do_tokenize(s):
    global T
    T = TData()
    i = 0
    l = len(s)
    while i < l:
        c = s[i]
        T.f = [T.y,i-T.yi+1]
        if T.nl: 
            T.nl = False
            i = do_indent(s,i,l)
        elif c == '\n': i = do_nl(s,i,l)
        elif c in _ISYMBOLS: i = do_symbol(s,i,l)
        elif c >= '0' and c <= '9': i = do_number(s,i,l)
        elif is_name_begin(c):  i = do_name(s,i,l)
        elif c=='"' or c=="'": i = do_string(s,i,l)
        elif c=='#': i = do_comment(s,i,l)
        elif c == '\\' and s[i+1] == '\n':
            i += 2; T.y+=1; T.yi = i
        elif c == ' ' or c == '\t': i += 1
        else: report_error('do_tokenize',s,Token('', '', T.f), "unknown token")
    indent(0)
    r = T.res
    T = None
    return r

def do_nl(s,i,l):
    if not T.braces:
        T.add('nl','nl')
    i+=1
    T.nl=True
    T.y+=1
    T.yi=i
    return i

def do_indent(s,i,l):
    v = 0
    while i<l:
        c = s[i]
        if c != ' ' and c != '\t': 
            break
        i+=1
        v+=1
    # skip blank line or comment line.
    # i >= l means reaching EOF, which do not need to indent or dedent
    if not T.braces and c != '\n' and c != '#' and i < l:
        indent(v)
    return i

def indent(v):
    if v == T.indent[-1]: pass
    elif v > T.indent[-1]:
        T.indent.append(v)
        T.add('indent',v)
    elif v < T.indent[-1]:
        n = T.indent.index(v)
        while len(T.indent) > n+1:
            v = T.indent.pop()
            T.add('dedent',v)


def str_match(s, target, start = 0):
    return s[start:start+len(target)] == target
            
def do_symbol(s,i,l):
    v = None
    for sb in SYMBOLS:
        if str_match(s, sb, i):
            i += len(sb)
            v = sb
            break
    if v == None:
        raise "invalid symbol"
    T.add(v,v)
    if v in _B_BEGIN: T.braces += 1
    if v in _END: T.braces -= 1
    return i

def do_number(s,i,l):
    v=s[i];i+=1;c=None
    while i<l:
        c = s[i]
        if (c < '0' or c > '9') and (c < 'a' or c > 'f') and c != 'x': break
        v+=c;i+=1
    if c == '.':
        v+=c;i+=1
        while i<l:
            c = s[i]
            if c < '0' or c > '9': break
            v+=c;i+=1
    T.add('number',float(v))
    return i

def is_name_begin(c):
    return (c>='a' and c<='z') or (c>='A' and c<='Z') or (c in '_$')
    
def is_name(c):
    return (c>='a' and c<='z') or (c>='A' and c<='Z') or (c in '_$') or (c>='0' and c<='9')
    
def do_name(s,i,l):
    v=s[i];i+=1
    while i<l:
        c = s[i]
        if not is_name(c): break
        v+=c
        i+=1
    if v in KEYWORDS: T.add(v,v)
    else: T.add('name',v)
    return i

def do_string(s,i,l):
    v = ''; q=s[i]; i+=1
    if (l-i) >= 5 and s[i] == q and s[i+1] == q: # """
        i += 2
        while i<l-2:
            c = s[i]
            if c == q and s[i+1] == q and s[i+2] == q:
                i += 3
                T.add('string',v)
                break
            else:
                v+=c; i+=1
                if c == '\n': T.y += 1;T.x = i
    else:
        while i<l:
            c = s[i]
            if c == "\\":
                i = i+1; c = s[i]
                if c == "n": c = '\n'
                elif c == "r": c = chr(13)
                elif c == "t": c = "\t"
                elif c == "0": c = "\0"
                elif c == 'b': c = '\b'
                v+=c;i+=1
            elif c == q:
                i += 1
                T.add('string',v)
                break
            else:
                v+=c;i+=1
    return i

def do_comment(s,i,l):
    i += 1
    value = ""
    while i<l:
        if s[i] == '\n': break
        value += s[i]
        i += 1
    if value.startswith("@debugger"):
        T.add("@", "debugger")
    return i

def loadfile(fname):
    with open(fname) as fp:
        return fp.read()

def main_test():
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
    fmt = "%-6s%-8s%-12s%s"
    print(fmt % ("index", "type", "pos", "val"))
    print("-" * 30)
    for index, token in enumerate(tokens):
        print(fmt % (index+1, token.type, token.pos, token.val))

if __name__ == "__main__":
    main_test()


