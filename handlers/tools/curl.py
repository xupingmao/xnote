# encoding=utf-8
from collections import OrderedDict
import os
import six
import socket, ssl
import re
import io
import gzip
import xutils
import xtemplate
import web
from xutils import splithost

_opener = None

def build_opener(*handlers):
    """Create an opener object from a list of handlers.

    The opener will use several default handlers, including support
    for HTTP, FTP and when applicable HTTPS.

    If any of the handlers passed as arguments are subclasses of the
    default handlers, the default handlers will not be used.
    """
    opener = OpenerDirector()
    default_classes = [UnknownHandler, HTTPHandler,
                       HTTPDefaultErrorHandler, HTTPRedirectHandler,
                       FTPHandler, FileHandler, HTTPErrorProcessor,
                       DataHandler]
    if hasattr(http.client, "HTTPSConnection"):
        default_classes.append(HTTPSHandler)
    skip = set()
    for klass in default_classes:
        for check in handlers:
            if isinstance(check, type):
                if issubclass(check, klass):
                    skip.add(klass)
            elif isinstance(check, klass):
                skip.add(klass)
    for klass in skip:
        default_classes.remove(klass)

    for klass in default_classes:
        opener.add_handler(klass())

    for h in handlers:
        if isinstance(h, type):
            h = h()
        opener.add_handler(h)
    return opener

# 从urllib.request中拷贝而来
def urlopen(url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
            cafile=None, capath=None, cadefault=False, context=None):
    global _opener
    if cafile or capath or cadefault:
        if context is not None:
            raise ValueError(
                "You can't pass both context and any of cafile, capath, and "
                "cadefault"
            )
        if not _have_ssl:
            raise ValueError('SSL support not available')
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
                                             cafile=cafile,
                                             capath=capath)
        https_handler = HTTPSHandler(context=context)
        opener = build_opener(https_handler)
    elif context:
        https_handler = HTTPSHandler(context=context)
        opener = build_opener(https_handler)
    elif _opener is None:
        _opener = opener = build_opener()
        install_opener(opener)
    else:
        opener = _opener
    return opener.open(url, data, timeout)


def proxy(method, fullurl, data="", headers=None):
    host, url = splithost(fullurl)
    con = HTTPConnection(host, timeout=10)
    try:
        # HTTPConnection.request(method, url[, body[, headers]])
        headers = {}
        headers["Content-Type"] = "text/html"
        headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.110 Safari/537.36"
        headers["Content-Length"] = len(data)

        headers.update(headers)
        # 设置Cookie
        # headers["Set-Cookie"] = ""
        con.request(method, url, data, headers)
        resp = con.getresponse()
        # byte buffer
        result = resp.read()
        return result
    except Exception as e:
        raise e
    finally:
        con.close()

def putheader(headers, header_name, wsgi_name):
    if wsgi_name in web.ctx.environ:
        headers[header_name] = web.ctx.environ[wsgi_name]

def get_host(url):
    # TODO 处理端口号
    return re.findall(r"https?://([^\s\?/]+)", url)[0]

class handler:

    # 使用低级API访问HTTP，可以任意设置header，data等
    # 但是返回结果也需要自己处理
    def do_http(self, method, addr, url, headers, data):
        self.status = ""
        cl = six.moves.http_client.HTTPConnection(addr)
        cl.request(method, url, data, headers = headers)
        head = None
        buf = None
        content_encoding = None

        if six.PY2:
            resp = cl.getresponse()
            buf = resp.read()
            resp.close()
        else:
            with cl.getresponse() as resp:
                self.response_headers = resp.getheaders()
                self.status = resp.getcode()
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
        return buf

    def GET(self):
        self.response_headers = []
        # url = web.ctx.environ["REQUEST_URI"]
        url = xutils.get_argument("url")
        body = xutils.get_argument("body")
        method = xutils.get_argument("method")
        content_type = xutils.get_argument("content_type")
        cookie = xutils.get_argument("cookie") or ""

        if url is None:
            return xtemplate.render("tools/curl.html")

        if not url.startswith("http"):
            url = "http://" + url
        url = xutils.quote_unicode(url)
        host = get_host(url)

        # print(url, method, host)
        # print(web.ctx.environ["HTTP_USER_AGENT"])
        headers = OrderedDict()
        headers["Connection"]    = "Keep-Alive"
        headers["Cache-Control"] = "max-age=0"
        headers["Content-Type"]  = content_type
        headers["Host"]   = host
        headers["Cookie"] = cookie
        # print(cookie)
    
        putheader(headers, "User-Agent", "HTTP_USER_AGENT")        
        putheader(headers, "Accept", "HTTP_ACCEPT")
        putheader(headers, "Accept-Encoding", "HTTP_ACCEPT_ENCODING")
        putheader(headers, "Accept-Language", "HTTP_ACCEPT_LANGUAGE")
        # putheader(headers, "Cookie", "HTTP_COOKIE")

        try:
            # response = b''.join(list(self.do_http(method, host, url, headers, data=body)))
            buf = self.do_http(method, host, url, headers, data=body)
            if isinstance(buf, bytes):
                response = xutils.decode_bytes(buf)
            else:
                response = buf
            # byte 0x8b in position 1 usually signals that the data stream is gzipped
        except Exception as e:
            xutils.print_exc()
            response = str(e)

        return xtemplate.render("tools/curl.html", url=url, 
            status = self.status,
            method=method, body=body, 
            response=response, cookie=cookie,
            response_headers = self.response_headers)


if __name__ == '__main__':
    main()
