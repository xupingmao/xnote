# encoding=utf-8
import codecs
import os
import platform
from . import logutil

''' read file '''
def readFile(path):
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

def read_utf8(path):
    fp = open(path, encoding="utf-8")
    content = fp.read()
    fp.close()
    return content

def read(path):
    return readFile(path)

def readfile(path):
    return readFile(path)

def readRawFile(path):
    fp = open(path, "rb")
    buf = fp.read(1024)
    while buf:
        yield buf
        buf = fp.read(1024)
    fp.close()

def writeFile(path, content):
    fp = open(path, "wb")
    buffer = codecs.encode(content, "utf-8")
    fp.write(buffer)
    fp.close()
    return content

def writefile(path, content):
    return writeFile(path, content)

def writebytes(path, bytes):
    dirname = os.path.dirname(path)
    check_create_dirs(dirname)
    fp = open(path, "wb")
    fp.write(bytes)
    fp.close()
    return bytes

def readbytes(path):
    fp = open(path, "rb")
    bytes = fp.read()
    fp.close()
    return bytes

def removeFile(fullpath, raiseIfNotExists = False):
    if os.path.exists(fullpath):
        os.remove(fullpath)
    elif raiseIfNotExists:
        raise Error("file not exits!")

def remove(path):
    removeFile(path)

def copy(src, dest):
    bufsize = 64 * 1024 # 64k
    srcfp = open(src, "rb")
    destfp = open(dest, "wb")

    try:
        buf = srcfp.read(bufsize)
        while buf:
            destfp.write(buf)
            buf = srcfp.read(bufsize)
    except Exception as e:
        logutil.error("copy file from {} to {} failed", src, dest, e)

    srcfp.close()
    destfp.close()

def check_create_dirs(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def getFileExt(fname):
    if '.' not in fname:return ''
    return fname.split('.')[-1]

def getReadableSize(size):
    if size < 1024:
        return '%s B' % size
    elif size < 1024 **2:
        return '%.2f K' % (float(size) / 1024)
    elif size < 1024 ** 3:
        return '%.2f M' % (float(size) / 1024 ** 2)
    else:
        return '%.2f G' % (float(size) / 1024 ** 3)

def format_size(size):
    if size < 1024:
        return '%s B' % size
    elif size < 1024 **2:
        return '%.2f K' % (float(size) / 1024)
    elif size < 1024 ** 3:
        return '%.2f M' % (float(size) / 1024 ** 2)
    else:
        return '%.2f G' % (float(size) / 1024 ** 3)

formatSize = format_size
        
def renameFile(srcname, dstname):
    destDirName = os.path.dirname(dstname)
    if not os.path.exists(destDirName):
        os.makedirs(destDirName)
    os.rename(srcname, dstname)


def openDirectory(dirname):
    if os.name == "nt":
        os.popen("explorer %s" % dirname)
    elif platform.system() == "Darwin":
        os.popen("open %s" % dirname)

def get_file_size(path, format=True):
    st = os.stat(path)
    if format:
        return format_size(st.st_size)
    return st.st_size