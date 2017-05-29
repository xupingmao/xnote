# encoding=utf-8
"""
压缩文件，对非ASCII码进行urlencode处理
"""
import zipfile
import os
import sys


def quote_unicode(url):
    def quote_char(c):
        # ASCII 范围 [0-127]
        if c <= 127:
            return chr(c)
        return '%%%02X' % c

    bytes = url.encode("utf-8")
    return ''.join([quote_char(c) for c in bytes])


def walk_dir(dirname, skip_hidden=True):
    dirs = []
    files = []
    for name in os.listdir(dirname):
        path = os.path.join(dirname, name)
        if skip_hidden and name.startswith("."):
            continue
        if os.path.isdir(path):
            dirs.append(name)
            yield from walk_dir(path, skip_hidden)
        elif os.path.isfile(path) or os.path.islink(path):
            files.append(name)
    yield dirname, dirs, files



def zip_dir(inputDir, outputFile, skip_hidden=True):
    # 创建目标文件
    absroot = os.path.abspath(outputFile)
    # print(absroot)
    with open(outputFile, "w"):
        pass
    zf = zipfile.ZipFile(outputFile, "w")

    for root, dirs, files in walk_dir(inputDir):
        for name in files:
            if skip_hidden and name.startswith("."):
                continue
            path = os.path.join(root, name)
            abspath = os.path.abspath(path)
            if abspath == absroot:
                # 跳过目标文件自身
                # print("Skip file", abspath)
                continue
            arcname = path[len(inputDir):]
            zf.write(path, quote_unicode(arcname))
    zf.close()

if __name__ == '__main__':
    zip_dir(sys.argv[1], sys.argv[2])