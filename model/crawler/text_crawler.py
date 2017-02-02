from BaseHandler import *
from bs4 import BeautifulSoup

def fetchpage(url):
    bytes = urlopen(url).read()
    for encoding in ("utf-8", "gbk", "gb2312"):
        try:
            return bytes.decode(encoding)
        except:
            pass
    raise Exception("can not decode content")

class handler(BaseHandler):

    def default_request(self):
        url = self.get_argument("url", "")
        if url == "":
            self.render("crawler/text_crawler.html", url=url)
            return
        url = netutil.get_http_url(url)
        content = fetchpage(url)
        soup = BeautifulSoup(content, "html.parser")

        imgs  = soup.find_all("img")
        links = soup.find_all("a")
        text  = soup.get_text()
        host = netutil.get_host(url)
        self.render("crawler/text_crawler.html", url=url, 
           texts = get_texts(soup), links = get_links(links), text = text)

def get_texts(soup):
    textlist = []
    divs = soup.find_all("div")

    for div in divs:
        text = div.get_text()
        if text in textlist:
            continue
        textlist.append(text)
    return textlist

def get_images(host, imgs):
    srclist = []
    for img in imgs:
        src = img.attrs.get("src")
        if src == None:
            continue
        if src.startswith("/"):
            src = host + src
        if src in srclist:
            continue
        srclist.append(src)
    return srclist

def get_links(links):
    return links

name = "文本爬虫"
description = "分析网站的文本"