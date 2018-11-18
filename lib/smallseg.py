# -*- coding:utf-8 -*-
# @author sunjoy <ccnusjy@gmail.com>
# @modified 2018/11/19 01:19:38
# source https://github.com/iurisilvio
# 基于最大匹配算法
from __future__ import print_function
import re
import os
import sys

PY3K = sys.version_info >= (3, 0)

if not PY3K:
    range = xrange

# 特殊字符，包括副词、助词、介词、姓氏
specialwords = "和是了中有都的来在次还但为里用外上下就以去即丁万乔余候傅冯刘单卢史叶吕吴唐夏姚姜孔孙孟宋尹崔常康廖张彭徐戴文方易曹曾朱李杜杨林梁武段毛江汤沈潘熊王田白石秦罗肖胡苏范董蒋薛袁谢谭贾赖赵邓邱邵邹郑郝郭金钟钱阎陆陈雷韩顾马高魏黄黎龙龚"


class SEG(object):
    def __init__(self, dictpath = None):
        _localDir = os.path.dirname(__file__)
        _curpath  = os.path.normpath(os.path.join(os.getcwd(),_localDir))
        curpath   = _curpath
        self.d    = {}
        self.debug("loading dict...")
        # 分词符号，可以自定义修改
        self.split_pattern = u"。|，|,|！|…|!|《|》|<|>|\"|'|:|：|？|\?|、|\||“|”|‘|’|；|—|（|）|·|\(|\)|　|\s|\[|\]"
        if dictpath is not None:
            self.load_words([x.rstrip() for x in open(dictpath).readlines()])
        self.specialwords= set([x for x in specialwords])
        self.debug('dict ok.')

    def debug(self, message):
        pass

    #set dictionary(a list)
    def load_words(self,keywords):
        """构造字典树（逆序）
        """
        p = self.d
        q = {}
        k = ''
        for word in keywords:
            word = (chr(11)+word)
            if len(word)>5:
                continue
            p = self.d
            ln = len(word)
            for i in range(ln-1,-1,-1):
                char = word[i].lower()
                if p=='':
                    q[k] = {}
                    p = q[k]
                if not (char in p):
                    p[char] = ''
                    q = p
                    k = char
                p = p[char]

    
    def _binary_seg(self,s):
        """把s分成若干个2元字组（逆序）
            >>> SEG()._binary_seg('今天天气不错')
            ['不错', '气不', '天气', '天天', '今天']
        """
        ln = len(s)
        if ln==1:
            return [s]
        R = []
        for i in range(ln,1,-1):
            tmp = s[i-2:i]
            R.append(tmp)
        return R
    
    def _pro_unreg(self,piece):
        """拆分句子成单词，返回单词列表（二元字组，没有匹配词典）
        :rtype list:
        """
        R = []
        # tmp = re.sub(u"。|，|,|！|…|!|《|》|<|>|\"|'|:|：|？|\?|、|\||“|”|‘|’|；|—|（|）|·|\(|\)|　"," ",piece).split()
        tmp = re.split(self.split_pattern, piece)
        ln1 = len(tmp)
        for i in range(len(tmp)-1,-1,-1):
            mc = re.split(r"([0-9A-Za-z\-\+#@_\.]+)",tmp[i])
            for j in range(len(mc)-1,-1,-1):
                r = mc[j]
                if re.search(r"([0-9A-Za-z\-\+#@_\.]+)",r)!=None:
                    # 处理英文单词
                    R.append(r)
                else:
                    R.extend(self._binary_seg(r))
        return R
        
        
    def cut(self,text):
        """切分单词，返回单词列表
        """
        # text = text
        p = self.d
        ln = len(text)
        # 右边游标
        i = ln 
        # 左边游标
        j = 0
        z = ln
        q = 0
        # 分词结果
        recognised = []
        # 存储临时变量
        mem = None
        mem2 = None
        while i-j>0:
            # 从后往前遍历
            t = text[i-j-1].lower()
            #print i,j,t,mem
            if not (t in p):
                # 不在字典树中
                if (mem!=None) or (mem2!=None):
                    # 后一个字不在字典树中
                    if mem!=None:
                        i,j,z = mem
                        mem = None
                    elif mem2!=None:
                        delta = mem2[0]-i
                        if delta>=1:
                            if (delta<5) and (re.search(r"[\w\u2E80-\u9FFF]",t)!=None):
                                pre = text[i-j]
                                #print pre
                                if not (pre in self.specialwords):
                                    i,j,z,q = mem2
                                    del recognised[q:]
                            mem2 = None
                            
                    p = self.d
                    if((i<ln) and (i<z)):
                        unreg_tmp = self._pro_unreg(text[i:z])
                        recognised.extend(unreg_tmp)
                    recognised.append(text[i-j:i])
                    #print text[i-j:i],mem2
                    i = i-j
                    z = i
                    j = 0
                    continue
                j = 0
                i -= 1
                p = self.d
                continue
            # 匹配字典树，再往前匹配一个字符
            p = p[t]
            j+=1
            if chr(11) in p:
                # 到达词库中单词的末端
                if j<=2:
                    mem = i,j,z
                    #print text[i-1]
                    if (z-i<2) and (text[i-1] in self.specialwords) and ((mem2==None) or ((mem2!=None and mem2[0]-i>1))):
                        #print text[i-1]
                        mem = None
                        mem2 = i,j,z,len(recognised)
                        p = self.d
                        i -= 1
                        j = 0
                    continue
                    #print mem
                p = self.d
                #print i,j,z,text[i:z]
                if((i<ln) and (i<z)):
                    unreg_tmp = self._pro_unreg(text[i:z])
                    recognised.extend(unreg_tmp)
                recognised.append(text[i-j:i])
                i = i-j
                z = i
                j = 0
                mem = None
                mem2 = None
        #print mem
        if mem!=None:
            i,j,z = mem
            recognised.extend(self._pro_unreg(text[i:z]))
            recognised.append(text[i-j:i])        
        else:
            # 没有匹配任何词库中的词语，就按最简单的二元字组划分
            recognised.extend(self._pro_unreg(text[i-j:z]))
        return recognised


if __name__ == "__main__":
    pass
