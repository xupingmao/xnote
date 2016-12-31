# utilities for xnote
import sys
import os

PY2 = sys.version_info[0] == 2

if PY2:
    from urllib import quote, unquote, urlopen
else:
    from urllib.parse import quote, unquote
    from urllib.request import urlopen

    
#################################################################
##   File System Utilities
#################################################################
def readfile(path, mode = "r"):
    ''' read file '''
    try:
        fp = open(path, encoding="utf-8")
        content = fp.read()
        fp.close()
        return content
    except:
        fp = open(path, encoding="gbk")
        content = fp.read()
        fp.close()
        return content
        
def savefile(path, content):
    import codecs
    fp = open(path, mode="wb")
    buf = codecs.encode(content, "utf-8")
    fp.write(buf)
    fp.close()
    return content
    
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