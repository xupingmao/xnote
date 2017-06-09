# encoding=utf-8

from handlers.base import *
from collections import OrderedDict

import http.client
import socket, ssl
import re

from urllib.request import Request, build_opener, HTTPSHandler, UnknownHandler
from urllib.request import HTTPHandler, HTTPDefaultErrorHandler, HTTPRedirectHandler
from urllib.request import FTPHandler, FileHandler, HTTPErrorProcessor
from urllib.request import DataHandler, OpenerDirector, install_opener

from http.client import HTTPConnection

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

def urlopen(url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
            *, cafile=None, capath=None, cadefault=False, context=None):
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

def do_http(method, addr, url, headers):
    print(addr, url)
    cl = HTTPConnection(addr)
    cl.request(method, url, None, headers = headers)
    head = None
    with cl.getresponse() as resp:
        # try:
        #     print(resp.decode("utf-8"))
        # except:
        #     print(resp.decode("gbk"))
        # finally:
        #     print(resp)
        if head:
            head = resp.read(1024*8)
            index = head.find("\r\n\r\n")
            yield head[index+4:]
        else:
            yield resp.read(1024)

def putheader(headers, header_name, wsgi_name):
    if wsgi_name in web.ctx.environ:
        headers[header_name] = web.ctx.environ[wsgi_name]

# from web.wsgiserver import wsgiserver

# def proxy_app(environ, start_response):
#     status = '200 OK'
#     response_headers = [('Content-type','text/plain')]
#     start_response(status, response_headers)
#     return ['Hello world!']



# def start():
#     global server
#     if server is not None:
#         server.stop()
#     server = wsgiserver.CherryPyWSGIServer(
#                 ('0.0.0.0', 8070), proxy_app,
#                 server_name='www.cherrypy.example')
#     server.start() 

# start()


def get_host(url):
    # TODO 处理端口号
    return re.findall(r"https?://([^\s\?]+)", url)[0]

class handler:

    def GET(self):
        # url = web.ctx.environ["REQUEST_URI"]
        url = web.input().url
        # print(web.ctx)
        # print(web.ctx.environ)
        method = web.ctx.method
        # host   = web.ctx.host

        host = get_host(url)

        # print(url, method, host)
        # print(web.ctx.environ["HTTP_USER_AGENT"])
        headers = OrderedDict()
        # return urlopen(url, context = headers)
        # input("wait")
        # req = Request(url, None, headers)
        # opener = build_opener(HTTPSHandler())
        # bytes = urlopen(req).read()
        # bytes = opener.open(req)
        # print(bytes)
        # print(web.ctx.environ)
        # headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Host"] = host
        headers["Connection"]   = "Keep-Alive"
        headers["Cache-Control"] = "max-age=0"
    
        putheader(headers, "User-Agent", "HTTP_USER_AGENT")        
        putheader(headers, "Accept", "HTTP_ACCEPT")
        putheader(headers, "Accept-Encoding", "HTTP_ACCEPT_ENCODING")
        putheader(headers, "Accept-Language", "HTTP_ACCEPT_LANGUAGE")
        putheader(headers, "Cookie", "HTTP_COOKIE")

        web.header("Content-Type", "text/html")
        req = Request(url, headers = headers)
        # return urlopen(url).read()
        return do_http(method, host, url, headers)
        # return urlopen(req).read()
        # for key in headers:
        #     print("%s = %s" % (key, headers[key]))
        # return do_http(method, host, url, headers)

if __name__ == '__main__':
    main()
