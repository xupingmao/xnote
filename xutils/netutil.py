# -*- coding:utf-8 -*-
# encoding=utf-8
# @modified 2021/11/28 19:47:17
# decode: bytes -> str
# encode: str -> bytes
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2021/11/28 19:47:17
@LastEditors  : xupingmao
@LastEditTime : 2023-01-22 00:50:55
@FilePath     : /xnote/xutils/netutil.py
"""

import os
import re
import codecs
import xutils.six as six
import socket
import io
import gzip
import logging

from xutils.imports import try_decode, quote
from xutils.base import print_exc

# TODO fix SSLV3_ALERT_HANDSHAKE_FAILURE on MacOS
try:
    # try py3 first
    from http.client import HTTPConnection
    from urllib.request import urlopen, Request

except ImportError as e:
    from urllib2 import urlopen, Request

try:
    import requests
except ImportError:
    requests = None

BUFSIZE = 1024 * 512

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.110 Safari/537.36"

_mock = None

def set_net_mock(mock):
    """设置单元测试mock"""
    global _mock
    _mock = mock

def splithost(url):
    """
        >>> splithost('//host[:port]/path')
        ('host[:port]', '/path')
        >>> splithost('http://www.baidu.com/index.html')
        ('www.baidu.com', '/index.html')
    """
    pattern = re.compile('^(http:|https:)?(//)?([^/?]*)(.*)$')
    match = pattern.match(url)
    if match: return match.group(3, 4)
    return None, url

def get_path(web_root, webpath):
    if len(webpath) > 0 and webpath[0] == "/":
        webpath = webpath[1:]
    if os.name == "nt":
        webpath = webpath.replace("/", "\\")
    return os.path.join(web_root, webpath)


def get_http_home(host):
    """
    >>> get_http_home("www.xnote.com")
    'http://www.xnote.com'
    >>> get_http_home("https://www.xnote.com")
    'https://www.xnote.com'
    """
    assert host != None
    if not host.startswith(("http://", "https://")):
        return "http://" + host
    return host

def get_http_url(url):
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url.split("#")[0]

def is_http_url(url):
    if not isinstance(url, str):
        return False

    if not url.startswith(("http://", "https://")):
        return False
    
    return True

def get_host_by_url(url):
    """
        >>> get_host("http://www.baidu.com/index.html")
        'www.baidu.com'
    """
    p = r"https?://([^\/]+)"
    m = re.match(p, url)
    if m and m.groups():
        return m.groups()[0]
    return None

def get_host(url):
    return get_host_by_url(url)


def get_local_ip_by_socket():
    """使用UDP协议获取当前的局域网地址
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("128.0.0.1", 80)) # 随便一个有效的IP地址即可
        host, port = s.getsockname()
        return host


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

def do_http(method, url, headers, data = None, charset = 'utf-8'):
    """使用低级API访问HTTP，可以任意设置header，data等
    """
    addr = get_host_by_url(url)
    if addr == None:
        raise Exception("invalid url (%s)" % url)

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

def http_get_by_requests(url, charset = None):
    assert requests != None
    resp = requests.get(url, headers = {"User-Agent": USER_AGENT})
    return resp.text

def build_query_string(params, *, skip_empty_value=False):
    temp = []
    for key in params:
        value = params[key]
        if skip_empty_value and (value == None or value == ""):
            continue
        temp.append("%s=%s" % (key, quote(value)))

    return "&".join(temp)

def _join_url_and_params(url, params, *, skip_empty_value=False):
    if params is None:
        return url

    query_string = build_query_string(params, skip_empty_value=skip_empty_value)
    if "?" in url:
        return url + "&" + query_string
    else:
        return url + "?" + query_string

def http_get(url, charset=None, params = None, skip_empty_value=False):
    """Http的GET请求"""
    url = _join_url_and_params(url, params, skip_empty_value=skip_empty_value)

    if _mock != None:
        # 用于单元测试mock
        return _mock.http_get(url, charset, params)

    if requests != None:
        return http_get_by_requests(url, charset)
    out = []
    bufsize = BUFSIZE
    readsize = 0

    # FIXME windows环境下有内存泄漏 安装requests可以解决这个问题
    conn = urlopen(url)
    try:
        chunk = conn.read(bufsize)
        while chunk:
            out.append(chunk)
            readsize += len(chunk)
            chunk = conn.read(bufsize)
        logging.info("get %s bytes", readsize)
        bytes = b''.join(out)
        if charset:
            return codecs.decode(bytes, charset)
        else:
            return try_decode(bytes)
    finally:
        conn.close()

def http_post(url, body='', charset='utf-8'):
    """HTTP的POST请求
    :arg str url: 请求的地址
    :arg str body: POST请求体
    :arg str charset: 字符集，默认utf-8
    """
    if _mock != None:
        return _mock.http_post(url, body, charset)
        
    status, headers, body = do_http("POST", url, None, body)
    return body

def http_download_by_requests(url, destpath):
    assert requests != None
    resp = requests.get(url, headers = {"User-Agent": USER_AGENT})
    with open(destpath, "wb") as fp:
        for chunk in resp.iter_content(chunk_size = BUFSIZE):
            fp.write(chunk)
    return resp.headers # headers是key大小写不敏感的dict

def http_download(address, destpath = None, dirname = None):
    if dirname is not None:
        basename = os.path.basename(address)
        destpath = os.path.join(dirname, basename)

    destpath = os.path.abspath(destpath)

    if requests is not None:
        return http_download_by_requests(address, destpath)

    bufsize = BUFSIZE
    address = get_http_url(address)
    headers = {
        "User-Agent": USER_AGENT
    }
    request = Request(address, headers = headers)
    stream  = urlopen(request)
    chunk   = stream.read(bufsize)
    dest    = open(destpath, "wb")

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


def get_file_ext_by_content_type(content_type):
        if content_type == "image/png":
            return ".png"

        if content_type == "image/jpg":
            return ".jpg"

        if content_type == "image/jpeg":
            return ".jpeg"

        if content_type == "image/gif":
            return ".gif"

        if content_type == "image/webp":
            return ".webp"

        if content_type == "image/svg+xml":
            return ".svg"

        return None