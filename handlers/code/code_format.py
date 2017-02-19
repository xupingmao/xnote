import sys, os


_name_list = ["_", "$"]

_blacklist = [
    "FindNextFile",
    "dwFileAttributes",
    "cFileName",
    "FindFirstFile"
]

_convert_dict = {
    "Tm_list": "TmList",
    "Tm_string": "TmString",
    "Tm_dict": "TmDict",
    "Tm_vm":"TmVm",
    "Tm_v_m": "TmVm",
    "Tm_function": "TmFunction",
    "Tm_value": "TmValue",
    "Tm_module": "TmModule",
    "Tm_frame": "TmFrame",
    "Tm_data": "TmData",
    "Parser_ctx":"ParserCtx",
    "Ast_node": "AstNode",
    "Asm_context" :"AsmContext",
    "Encode_ctx": "EncodeCtx",
    "Dict_node": "DictNode",
}

def do_name(line, i):
    newname = ''
    oldname = ''
    while i < len(line):
        c = line[i]
        if c.isalnum() or c in _name_list:
            oldname += c
            if c.isupper():
                newname += "_" + c.lower()
            else:
                newname += c
        else:
            break
        i+=1
    if oldname in _blacklist:
        return oldname, i 
    if oldname in _convert_dict:
        return _convert_dict[oldname], i
    if oldname[0].isupper():
        return oldname, i
    return newname, i

def do_skip_str(line, i, end):
    str = line[i]
    i += 1 # skip start char (',")
    while i < len(line):
        c = line[i]
        str += c
        if c == end:
            i += 1
            break
        if c == '\\':
            str += line[i+1]
            i += 2
        else:
            i += 1
    return str, i

def convert (content):
    buf = []
    i = 0
    while i < len(content):
        c = content[i]
        if c == '"' or c == "'":
            str, i = do_skip_str(content, i, c)
            buf.append(str)
        elif c.isalpha() or c in _name_list:
            newname, i = do_name(content, i)
            buf.append(newname)
        else:
            buf.append(c)
            i+=1
    return "".join(buf)

def save_file(name, content):
    fp = open(name, "w+")
    fp.write(content)
    fp.close()


def do_file(name):
    name = sys.argv[1]
    content = open(name).read()
    result = convert(content)
    if content != result:
        save_file(name + ".bak", content)
        save_file(name, result)

def do_dir(dirname):
    for root, dirs, files in os.walk(dirname):
        for f in files:
            name, ext = os.path.splitext(f)
            if ext not in ('.py', '.c'):
                continue
            abspath = os.path.join(root, f)
            do_file(abspath)
        
def do_test():
    origin = '''
    this is a test.
    I Am A Test (this will not be convert)
    ClassName will not be converted
    CONST will not be converted
    funcName will be converted
    "stringTest" will not be converted
    _testName will be converted
    '''
    print("origin:")
    print(origin)
    
    result = convert(origin)
    print("result")
    print(result)
            
def print_usage():
    print("usage:")
    print("  %s filename" % sys.argv[0])
    print("  %s -d dirname" % sys.argv[0])
            
if __name__ == '__main__':
    if len(sys.argv) == 2:
        opt = sys.argv[1]
        if opt == "-test":
            do_test()
            exit(0)
        else:
            do_file(opt)
            exit(0)
    elif len(sys.argv) == 3:
        opt = sys.argv[1]
        if opt == "-d":
            do_dir(opt, sys.argv[2])
            exit(0)
    print ("usage %s filename" % sys.argv[0])