from BaseHandler import *
from web.tornado.escape import xhtml_escape

CODE_EXT_LIST = (".java", 
                 ".c",
                 ".h",
                 ".cpp",
                 ".hpp",
                 ".vm",
                 ".html",
                 ".xml",
                 ".js",
                 ".py",
                 ".json",
                 ".text",
                 ".xsd")


class CodeAnalyzeHandler(BaseHandler):
    """analyze code"""

    def search_files(self, path, key, filename):
        if not os.path.isdir(path):
            raise Exception("%s is not a directory" % path)
        result_list = []
        for root, dirs, files in os.walk(path):
            for fname in files:
                name, ext = os.path.splitext(fname)
                if ext not in CODE_EXT_LIST:
                    continue
                if fname.startswith("._"):
                    # pass mac os temp files
                    continue
                fpath = os.path.join(root, fname)
                if filename != "" and not textutil.like(fname, filename):
                    # filename do not match
                    continue
                try:
                    content = fsutil.readfile(fpath)
                except Exception as e:
                    result_list.append(Storage(name=fpath, result=["read file fail, e=%s" % e]))
                result = textutil.find(content, key, show_line = True)
                if key != "" and len(result) == 0:
                    # key do not match
                    continue

                result_list.append(Storage(name=fpath, result = result))
        return result_list

    def default_request(self):
        path = self.get_argument("path", "")
        key  = self.get_argument("key", "")
        filename = self.get_argument("filename", "")
        try:
            if path != "":
                path = path.strip()
                key  = key.strip()
                filename = filename.strip()
                self.render("code/code-analyze.html", files = self.search_files(path, key, filename))
            else:
                self.render("code/code-analyze.html")
        except Exception as e:
            self.render("code/code-analyze.html", error = e)

handler = CodeAnalyzeHandler

searchkey = "code,代码分析工具"

name = "代码分析工具"
description = "对代码进行全文检索"