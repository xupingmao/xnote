# encoding=utf-8
# @modified 2018/11/16 02:29:08
import os
import re
import codecs
import six

try:
    # try py3 first
    from http.client import HTTPConnection
    from urllib.request import urlopen
except ImportError as e:
    from urllib2 import urlopen

BUFSIZE = 1024 * 512

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.110 Safari/537.36"

def splithost(url):
    """
        >>> splithost('//host[:port]/path')
        ('host[:port]', '/path')
        >>> splithost('http://www.baidu.com/index.html')
        ('www.baidu.com', '/index.html')
    """
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
        url = "http://" + url
    return url.split("#")[0]

def get_host(url):
    """
        >>> get_host("http://www.baidu.com/index.html")
        'www.baidu.com'
    """
    p = r"https?://([^\/]+)"
    m = re.match(p, url)
    if m and m.groups():
        return m.groups()[0]
    return None

class HttpResource:

    def __init__(self, url):
        self.url = get_http_url(url)
        self.protocol = url.split("://")[0]
        self.domain, _ = splithost(url)

    def get_res_url(self, url):
        """
            >>> HttpResource("http://www.a.com").get_res_url("https://b.com/b.png")
            'https://b.com/b.png'
            >>> HttpResource("http://www.a.com").get_res_url("//b.com/b.png")
            'http://b.com/b.png'
            >>> HttpResource("http://www.a.com").get_res_url("/b.png")
            'http://www.a.com/b.png'
            >>> HttpResource("http://www.a.com/a").get_res_url("b.png")
            'http://www.a.com/a/b.png'
        """
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith("//"):
            return "http:" + url
        if url[0] == '/':
            # 绝对路径
            return self.protocol + "://" + self.domain + url
        # 相对路径
        return self.url.rstrip("/") + "/" + url

    def get_res(self, url):
        return HttpResource(self.get_res_url(url))

    def get(self, charset = 'utf-8'):
        return http_get(self.url, charset)

class HttpResponse:

    def __init__(self, status, headers, content):
        self.status = status
        self.headers = headers
        self.content = content

def do_http(method, url, headers, data=None, charset='utf-8'):
    """使用低级API访问HTTP，可以任意设置header，data等
    """
    addr = get_host(url)
    if url.startswith("https://"):
        conn = six.moves.http_client.HTTPSConnection(addr)
    else:
        conn = six.moves.http_client.HTTPConnection(addr)
    headers = headers or dict()
    if "User-Agent" not in headers:
        headers["User-Agent"] = USER_AGENT
    conn.request(method, url, data, headers = headers)
    head = None
    buf = None
    response_headers = None
    with conn.getresponse() as resp:
        response_headers = resp.getheaders()
        content_type = resp.getheader("Content-Type")
        content_encoding = resp.getheader("Content-Encoding")
        buf = resp.read()
        if content_encoding == "gzip":
            fileobj = io.BytesIO(buf)
            gzip_f = gzip.GzipFile(fileobj=fileobj, mode="rb")
            content = gzip_f.read()
            return resp.getcode(), response_headers, content
        elif content_encoding != None:
            raise Exception("暂不支持%s编码" % content_encoding)
        return resp.getcode(), response_headers, codecs.decode(buf, charset)

def http_get(url, charset='utf-8'):
    """Http的GET请求"""
    out = []
    bufsize = BUFSIZE
    readsize = 0

    stream = urlopen(url)
    chunk = stream.read(bufsize)
    while chunk:
        out.append(chunk)
        readsize += len(chunk)
        chunk = stream.read(bufsize)
    print("get %s bytes" % readsize)
    bytes = b''.join(out)
    return codecs.decode(bytes, charset)

def http_post(url, body='', charset='utf-8'):
    """HTTP的POST请求
    :arg str url: 请求的地址
    :arg str body: POST请求体
    :arg str charset: 字符集，默认utf-8
    """
    status, headers, body = do_http("POST", url, None, body)
    return body

def http_download(address, destpath = None, dirname = None):
    bufsize = BUFSIZE
    address = get_http_url(address)
    stream = urlopen(address)
    chunk = stream.read(bufsize)
    if dirname is not None:
        basename = os.path.basename(address)
        destpath = os.path.join(dirname, basename)
    dest = open(destpath, "wb")
    try:
        readsize = 0
        while chunk:
            readsize += len(chunk)
            print("download %s bytes" % readsize)
            dest.write(chunk)
            chunk = stream.read(bufsize)
        print("download %s bytes, saved to %s" % (readsize, destpath))
    finally:
        dest.close()
