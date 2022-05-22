# encoding=utf-8
# created by xupingmao on 2017/04/22
from __future__ import print_function
import logging
import os
import time
import xtemplate
import xutils
import xauth
import xmanager
import xconfig
from bs4 import BeautifulSoup
from html2text import HTML2Text
from xutils import netutil
from xutils import Storage


def get_addr(src, host):
    if src is None:
        return None
    if src.startswith("//"):
        return "http:" + src
    return src


def readhttp(url):
    url = xutils.quote_unicode(url)
    return netutil.http_get(url)


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
    return str == None or len(str) == 0


def bs_get_text(result, element, blacklist=None):
    if blacklist is None:
        blacklist = []
    if element.name in blacklist:
        return
    result.append(element.get_text(recursive=False))
    for child in element.children:
        bs_get_text(result, child, blacklist)


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


def save_to_archive_dir(name):
    dirname = os.path.join(xconfig.DATA_DIR, time.strftime("archive/%Y/%m/%d"))
    xutils.makedirs(dirname)
    path = os.path.join(dirname, "%s_%s.md" % (name, time.strftime("%H%M%S")))
    xutils.savetofile(path, text)
    print("save file %s" % path)


def get_html_title(soup):
    title = soup.title
    if title != None:
        return title.get_text()


def import_from_html(html, baseurl=""):
    soup = BeautifulSoup(html, "html.parser")
    element_list = soup.find_all(["script", "style"])
    for element in element_list:
        element.extract()
    plain_text = soup.get_text(separator=" ")
    plain_text = clean_whitespace(plain_text)

    images = soup.find_all("img")
    links = soup.find_all("a")
    csses = soup.find_all("link")
    scripts = soup.find_all("script")
    title = get_html_title(soup)

    h = HTML2Text(baseurl=baseurl)
    text = "From %s\n\n" % baseurl + h.handle(html)

    texts = [text]
    images = get_addr_list(images)
    scripts = get_addr_list(scripts)

    return Storage(plain_text=plain_text,
                   title=title,
                   links=links,
                   csses=csses,
                   scripts=scripts,
                   texts=texts
                   )


class handler:

    template_path = "note/page/html_importer.html"

    def GET(self):
        address = xutils.get_argument("url")
        save = xutils.get_argument("save")
        user_name = xauth.current_name()

        # 添加日志
        xmanager.add_visit_log(user_name, "/note/html_importer")

        if save != "" and save != None:
            return self.POST()
        return xtemplate.render(self.template_path,
                                show_aside=False,
                                address=address, url=address)

    @xauth.login_required()
    def POST(self):
        try:
            file = xutils.get_argument("file", {})
            address = xutils.get_argument("url", "")
            name = xutils.get_argument("name", "")
            filename = ""

            if hasattr(file, "filename"):
                filename = file.filename

            if not isempty(address):
                address = address.strip()
                html = readhttp(address)
                filename = address
            else:
                # 读取文件
                html = ""
                for chunk in file.file:
                    html += chunk.decode("utf-8")

            logging.info("import html, filename={}, length={}, type={}".format(filename, len(html), type(html)))

            result = import_from_html(html, address)

            if name != "" and name != None:
                save_to_archive_dir(name)

            kw = dict(
                show_aside=False,
                address=address,
                url=address,
                images=result.images,
                links=result.links,
                csses=result.csses,
                scripts=result.scripts,
                texts=result.texts,
                article_title=result.title,
                plain_text=result.plain_text
            )

            return xtemplate.render(self.template_path, **kw)
        except Exception as e:
            xutils.print_stacktrace()
            return xtemplate.render(self.template_path,
                                    show_aside=False,
                                    error=str(e))


xutils.register_func("note.import_from_html", import_from_html)
