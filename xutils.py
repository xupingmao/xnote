# encoding=utf-8
# utilities for xnote
import sys
import os

PY2 = sys.version_info[0] == 2

if PY2:
    from urllib import quote, unquote, urlopen
    # from commands import getstatusoutput
else:
    from urllib.parse import quote, unquote
    from urllib.request import urlopen
    from subprocess import getstatusoutput

# 关于Py2的getstatusoutput，实际上是对os.popen的封装
# 而Py3中的getstatusoutput则是对subprocess.Popen的封装
# Py2的getstatusoutput, 注意原来的windows下不能正确运行，但是下面改进版的可以运行

if PY2:
    def getstatusoutput(cmd):
        ## Return (status, output) of executing cmd in a shell.
        import os
        # old
        # pipe = os.popen('{ ' + cmd + '; } 2>&1', 'r')
        pipe = os.popen(cmd + ' 2>&1', 'r')
        text = pipe.read()
        sts = pipe.close()
        if sts is None: sts = 0
        if text[-1:] == '\n': text = text[:-1]
        return sts, text
    
#################################################################
##   File System Utilities
#################################################################
def readfile(path, mode = "r"):
    '''
    读取文件，尝试多种编码，编码别名参考标准库Lib/encodings/aliases.py
        utf-8 是一种边长编码，兼容ASCII
        gbk 是一种双字节编码，全称《汉字内码扩展规范》，兼容GB2312
        latin_1 是iso-8859-1的别名，单字节编码，兼容ASCII
    '''
    for encoding in ["utf-8", "gbk", "mbcs", "latin_1"]:
        try:
            fp = open(path, encoding=encoding)
            content = fp.read()
            fp.close()
            return content
        except:
            pass
    raise Exception("can not read file %s" % path)
        
def savetofile(path, content):
    import codecs
    fp = open(path, mode="wb")
    buf = codecs.encode(content, "utf-8")
    fp.write(buf)
    fp.close()
    return content
    
savefile = savetofile

def backupfile(path, backup_dir = None, rename=False):
    if os.path.exists(path):
        if backup_dir is None:
            backup_dir = os.path.dirname(path)
        name   = os.path.basename(path)
        newname = name + ".bak"
        newpath = os.path.join(backup_dir, newname)
        # need to handle case that bakup file exists
        import shutil
        shutil.copyfile(path, newpath)
        
def get_pretty_file_size(path = None, size = None):
    if not size:
        size = os.stat(path).st_size
    if size < 1024:
        return '%s B' % size
    elif size < 1024 **2:
        return '%.2f K' % (float(size) / 1024)
    elif size < 1024 ** 3:
        return '%.2f M' % (float(size) / 1024 ** 2)
    else:
        return '%.2f G' % (float(size) / 1024 ** 3)
    
def get_file_size(path, format=True):
    st = os.stat(path)
    if format:
        return get_pretty_file_size(size = st.st_size)
    return st.st_size
    
    
def makedirs(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def touch(path):
    if not os.path.exists(path):
        with open(path, "wb") as fp:
            pass
    
#################################################################
##   DateTime Utilities
#################################################################



#################################################################
##   Str Utilities
#################################################################


#################################################################
##   Html Utilities, Python 2 do not have this file
#################################################################
def html_escape(s, quote=True):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true (the default), the quotation mark
    characters, both double quote (") and single quote (') characters are also
    translated.
    """
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace('\'', "&#x27;")
    return s
    
from web.tornado.escape import xhtml_escape
    
#################################################################
##   Platform/OS Utilities, Python 2 do not have this file
#################################################################

def is_windows():
    return os.name == "nt"