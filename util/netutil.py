# encoding=utf-8
import os
import re

try:
    from http.client import HTTPConnection
except ImportError as e:
    pass

def splithost(url):
    """splithost('//host[:port]/path') --> 'host[:port]', '/path'."""
    pattern = re.compile('^(http:|https:)?//([^/?]*)(.*)$')
    match = pattern.match(url)
    if match: return match.group(2, 3)
    return None, url

def get_path(web_root, web_path):
    if web_path[0] == "/":
        web_path = web_path[1:]
    if os.name == "nt":
        web_path = web_path.replace("/", "\\")
    return os.path.join(web_root, web_path)


def get_http_home(host):
    if not host.startswith(("http://", "https://")):
        return "http://" + host
    return host

def get_http_url(url):
    if not url.startswith(("http://", "https://")):
        return "http://" + url
    return url

def get_host(url):
    p = r"https?://([^\/]+)"
    m = re.match(p, url)
    if m and m.groups():
        return m.groups()[0]
    return None

# 使用低级API访问HTTP，可以任意设置header，data等
def do_http(method, url, headers, data=None):
    addr = get_host(url)
    cl = HTTPConnection(addr)
    cl.request(method, url, data, headers = headers)
    head = None
    buf = None
    response_headers = None
    with cl.getresponse() as resp:
        response_headers = resp.getheaders()
        content_type = resp.getheader("Content-Type")
        content_encoding = resp.getheader("Content-Encoding")
        buf = resp.read()
        if content_encoding == "gzip":
            fileobj = io.BytesIO(buf)
            gzip_f = gzip.GzipFile(fileobj=fileobj, mode="rb")
            content = gzip_f.read()
            return content
        elif content_encoding != None:
            raise Exception("暂不支持%s编码" % content_encoding)
        return resp.getcode(), response_headers, buf
