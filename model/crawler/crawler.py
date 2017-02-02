from BaseHandler import *
from bs4 import BeautifulSoup

def fetchpage(url):
    bytes = urlopen(url).read()
    try:
        return bytes.decode("utf-8")
    except:
        return bytes.decode("gbk")

class handler(BaseHandler):

    def default_request(self):
        url = self.get_argument("url", "")
        if url == "":
            self.render("crawler/crawler.html", url=url)
            return
        url = netutil.get_http_url(url)
        content = fetchpage(url)
        soup = BeautifulSoup(content)

        imgs  = soup.find_all("img")
        links = soup.find_all("a")
        text  = soup.get_text()
        host = netutil.get_host(url)
        self.render("crawler/crawler.html", url=url, 
            imgs = get_images(host, imgs), links = get_links(links), text = text)

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

name = "爬虫"
description = "分析网站的图片、链接"