# encoding=utf-8
# @modified 2019/02/16 23:03:27
# decode: bytes -> str
# encode: str -> bytes
import os
import re
import codecs
import six
import socket
from .imports import try_decode

# TODO fix SSLV3_ALERT_HANDSHAKE_FAILURE on MacOS
try:
    # try py3 first
    from http.client import HTTPConnection
    from urllib.request import urlopen, Request

except ImportError as e:
    from urllib2 import urlopen, Request

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
        if not url:
            return None
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

def http_get(url, charset=None):
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
    if charset:
        return codecs.decode(bytes, charset)
    else:
        return try_decode(bytes)

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
    headers = {
        "User-Agent": USER_AGENT
    }
    request = Request(address, headers = headers)
    stream = urlopen(request)
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

def tcp_send(domain, port, content, timeout=1, on_recv_func=None):
    """发送TCP请求, 由于TCP协议没有终止标识，超时就返回所有结果
    @param {string} domain 域名
    @param {integer} port 端口号
    @param {bytes|str} content 发送内容
    @param {function} on_recv_func 自定义处理tcp包的函数，返回True继续，返回False中断
    @return {bytes} 返回结果
    """
    TIMEOUT = timeout
    BUFSIZE = 1024

    data = content
    if isinstance(content, str):
        data = content.encode("utf-8")
    ip = socket.gethostbyname(domain)

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(conn, "settimeout"):
        # timeout单位是秒
        conn.settimeout(TIMEOUT)
    conn.connect((ip, port))
    conn.sendall(data)
    result = []
    try:
        # 使用文件同样会抛出socket.timeout异常，无法判断文件EOF
        # fp = conn.makefile()
        while True:
            buf = conn.recv(BUFSIZE)
            if not buf:break
            result.append(buf)
            if on_recv_func:
                if not on_recv_func(buf):
                    break
    except socket.timeout:
        # FIXME 如果真的是超时怎么办
        return b''.join(result)
    finally:
        conn.close()
    return b''.join(result)


