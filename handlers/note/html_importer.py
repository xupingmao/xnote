# encoding=utf-8
# created by xupingmao on 2017/04/22
from __future__ import print_function
import os
import urllib.request
import web
import time
import xtemplate
import xutils
import xauth
import xmanager
import xtables
import xconfig
from threading import Timer
from bs4 import BeautifulSoup
from html2text import HTML2Text

def get_addr(src, host):
    if src is None:
        return None
    if src.startswith("//"):
        return "http:" + src
    return src

def readhttp(address):
    address = xutils.quote_unicode(address)
    req = urllib.request.Request(
                    address, 
                    data=None, 
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                    }
                )
    bytes = xutils.urlopen(req).read()
    return xutils.decode_bytes(bytes)

def get_addr_list(images, host=None):
    dest = set()
    for image in images:
        src = image.attrs.get("src")
        src = get_addr(src, host)
        if src is not None:
            dest.add(src)
    return list(dest)

def get_text_list(elements):
    dest = set()
    for ele in elements:
        text = ele.get_text()
        if text is not None and len(text) > 0:
            dest.add(text)
    return list(dest)

def get_res_name(url):
    slash_pos = url.rfind("/")
    return url[slash_pos+1:]

def download_res_list(reslist, dirname):
    dirname = os.path.join("./tmp", dirname)
    xutils.makedirs(dirname)

    for res in reslist:
        print("Download", res)
        res = xutils.quote_unicode(res)
        bytes = xutils.urlopen(res).read()
        name = get_res_name(res)
        path = os.path.join(dirname, name)
        with open(path, "wb") as fp:
            fp.write(bytes)

def isempty(str):
    return str==None or len(str) == 0

def bs_get_text(result, element, blacklist=None):
    if blacklist is None:
        blacklist = []
    if element.name in blacklist:
        return
    result.append(element.get_text(recursive=False))
    for child in element.children:
        get_text(result, child, blacklist)

def clean_whitespace(text):
    buf = xutils.StringIO()
    buf.seek(0)
    whitespace = " \t\r\n\b"
    prev = "\0"
    for c in text:
        if c in whitespace and prev in whitespace:
            prev = c
            continue
        prev = c
        buf.write(c)
    buf.seek(0)
    return buf.read()

class handler:

    template_path = "note/tools/html_importer.html"

    def GET(self):
        address = xutils.get_argument("url")
        save  = xutils.get_argument("save")
        if save != "" and save != None:
            return self.POST()
        return xtemplate.render(self.template_path, 
            show_aside = False,
            address=address, url=address)

    @xauth.login_required()
    def POST(self):
        try:
            file     = xutils.get_argument("file", {})
            address  = xutils.get_argument("url", "")
            name     = xutils.get_argument("name", "")
            filename = ""

            if hasattr(file, "filename"):
                filename = file.filename
            plain_text = ""

            if not isempty(address):
                html = readhttp(address)
            else:
                # 读取文件
                html = ""
                for chunk in file.file:
                    html += chunk.decode("utf-8")

            print("Read html, filename={}, length={}".format(filename, len(html)))


            soup = BeautifulSoup(html, "html.parser")
            element_list = soup.find_all(["script", "style"])
            for element in element_list:
                element.extract()
            plain_text = soup.get_text(separator=" ")
            plain_text = clean_whitespace(plain_text)

            images = soup.find_all("img")
            links  = soup.find_all("a")
            csses  = soup.find_all("link")
            scripts = soup.find_all("script")
            # texts = soup.find_all(["p", "span", "div", "h1", "h2", "h3", "h4"])

            h = HTML2Text(baseurl = address)
            text = "From %s\n\n" % address + h.handle(html)

            texts = [text]

            images  = get_addr_list(images)
            scripts = get_addr_list(scripts)

            if name != "" and name != None:
                dirname = os.path.join(xconfig.DATA_DIR, time.strftime("archive/%Y/%m/%d"))
                xutils.makedirs(dirname)
                path = os.path.join(dirname, "%s_%s.md" % (name, time.strftime("%H%M%S")))
                xutils.savetofile(path, text)
                print("save file %s" % path)

            if False:
                user_name = xauth.get_current_name()
                xutils.call("note.create", 
                    name = name, 
                    content = content, 
                    type = "md", 
                    tags = ["来自网络"],
                    creator = user_name)

            return xtemplate.render(self.template_path,
                show_aside = False,
                images = images,
                links = links,
                csses = csses,
                scripts = scripts,
                texts = texts,
                address = address,
                url = address,
                plain_text = plain_text)
        except Exception as e:
            xutils.print_stacktrace()
            return xtemplate.render(self.template_path,
                show_aside = False,
                error = str(e))




