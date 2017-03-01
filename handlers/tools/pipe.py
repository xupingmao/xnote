# encoding=utf-8
"""数据管道

    通过类似于shell管道的方式来操作数据，有如下特征
    1. 入参出参都是str
    2. 使用换行分割数据
    3. 支持流式处理，一行为一个基本单位
    4. 通过组合pipe来处理数据
"""

import re
import web
import xtemplate


class Counter:

    def __init__(self, sorted=False):
        self.dict = {}

    def incr(self, key):
        if key in self.dict:
            self.dict[key] += 1
        else:
            self.dict[key] = 1
    
    def decr(self, key):
        if key in self.dict:
            self.dict[key] -= 1
        else:
            self.dict[key] = -1
            
#    def __iter__(self):
#        return list(self.dict.keys())
            
    def __str__(self):
        return str(self.dict)

def count(input_text):
    p = re.compile(r'"_tid": (\d+)')
    # result = []
    ct = Counter()
    for line in p.findall(input_text):
        # result.append(line)
        ct.incr(line)
        
    # return '\n'.join(result)
    return ct
    

class handler:

    def GET(self):
        return xtemplate.render("tools/pipe.html")

    def POST(self):
        # 处理上传文件
        # 必须初始化成{}
        args = web.input(file={})
        file = args.file

        if file is None:
            return self.GET()

        print(file.filename)

        with open("./tmp/in.txt", "wb") as fp:
            for chunk in file.file:
                fp.write(chunk)
        return self.GET()

