# encoding=utf-8
# created by xupingmao on 2017/04/22
import os
import web
import xtemplate
import xutils
from bs4 import BeautifulSoup

def get_addr(src, host):
    if src is None:
        return None
    if src.startswith("//"):
        return "http:" + src
    return src

def readhttp(address):
    bytes = xutils.urlopen(address).read()
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
        bytes = xutils.urlopen(res).read()
        name = get_res_name(res)
        path = os.path.join(dirname, name)
        with open(path, "wb") as fp:
            fp.write(bytes)

def isempty(str):
    return str==None or len(str) == 0

class handler:

    def GET(self):
        return xtemplate.render("tools/split_html.html")

    def POST(self):
        args = web.input(file={}, download_res="off")
        file = args.file
        download_res = args.download_res == "on"
        address = args.address

        filename = file.filename

        if not isempty(address):
            html = readhttp(address)
        else:
            html = ""
            for chunk in file.file:
                html += chunk.decode("utf-8")
        print("Read html, filename={}, length={}".format(filename, len(html)))

        soup = BeautifulSoup(html, "html.parser")
        images = soup.find_all("img")
        links  = soup.find_all("a")
        csses  = soup.find_all("link")
        scripts = soup.find_all("script")
        # texts = soup.find_all(["p", "span", "div", "h1", "h2", "h3", "h4"])
        texts = [soup.get_text()]

        images = get_addr_list(images)
        scripts = get_addr_list(scripts)
        # texts = get_text_list(texts)

        if download_res:
            download_res_list(images, filename)

        return xtemplate.render("tools/split_html.html",
            images = images,
            links = links,
            csses = csses,
            scripts = scripts,
            texts = texts)




