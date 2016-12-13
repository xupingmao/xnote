import sys, os
import urllib
import posixpath
import time

import web.webapi as web
from web.py3helpers import PY2

if PY2:
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
else:
    from http.server import HTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler

try:
    from urllib import parse as urlparse
    from urllib.parse import unquote
except ImportError:
    import urlparse
    from urllib import unquote

try:
    from io import BytesIO
except ImportError:
    from StringIO import BytesIO

import pdb
import io
import xutils
from BaseHandler import *
import config


class MyStaticApp(SimpleHTTPRequestHandler):
    """WSGI application for serving static files."""
    def __init__(self, environ, start_response):
        self.headers = []
        self.environ = environ
        self.start_response = start_response

    def send_response(self, status, msg=""):
        self.status = str(int(status)) + " " + msg

    def send_header(self, name, value):
        #the int(status) call is needed because in Py3 status is an enum.IntEnum and we need the integer behind
        value = str(value)
        for kv in self.headers:
            if kv[0] == name:
                self.headers.remove(kv)
        self.headers.append((name, value))

    def get_header(self, name):
        for key, value in self.headers:
            if name == key:
                return value

    def end_headers(self):
        pass

    def log_message(*a): pass


    def get_date_str(self):
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def send_range(self, f, block_size):
        total_size = self._m_total_size;
        http_range = self._m_http_range;
        start      = self.range_start
        end        = self.range_end
        f.seek(start)
        buf = f.read(block_size)
        f.close()
        self.send_header("Content-Range", "bytes %s-%s/%s" % (start, start+len(buf)-1, total_size))
        self.send_header("Content-Length", str(len(buf)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", self._filename)
        # self.send_header("Content-Type", "application/octet-stream")
        self.send_response(206,"Partial Content")
        # self.send_response(200, "OK")
        self.start_response(self.status, self.headers)

        content_range = self.get_header("Content-Range")
        content_length = str(len(buf))
        print("%s - - [%s]" % (self.client_address, self.get_date_str()))
        print("  - - HTTP_RANGE", http_range)
        print("  - - Content-Range", content_range)
        print("  - - Content-Length", content_length)
        # print("  - - Content-Disposition", self._filename)
        return buf

    def send_fixed_range(self, f, block_size):
        total_size = self._m_total_size;
        http_range = self._m_http_range;
        start      = self.range_start
        end        = self.range_end
        f.seek(start)

        content_range = "bytes %s-%s/%s" % (start, end, total_size)
        content_length = str(end - start + 1)
        print("%s - - [%s]" % (self.client_address, self.get_date_str()))
        print("  - - HTTP_RANGE", http_range)
        print("  - - Content-Range", content_range)
        print("  - - Content-Length", content_length)
        print("  - - Content-Disposition", self._filename)

        self.send_header("Content-Range", content_range)
        self.send_header("Content-Length", content_length)
        self.send_header("Accept-Ranges", "bytes")
        # self.send_header("Content-Disposition", self._filename)
        # self.send_header("Content-Type", "application/octet-stream")
        self.send_response(206,"Partial Content")
        # self.send_response(200, "OK")
        self.start_response(self.status, self.headers)

        while start <= end:
            rest_size = end - start + 1
            if rest_size <= 0:
                raise StopIteration()
            size = block_size
            if rest_size < block_size:
                size = rest_size
            buf = f.read(size)
            start += len(buf)
            yield buf

    def __iter__(self):
        environ = self.environ

        self.path = environ.get('PATH_INFO', '')
        # marked
        # print (type(self.path))
        # print (os.stat(self.path))
        # it words well in python alone, the bug should be cherrypy
        self.client_address = environ.get('REMOTE_ADDR','-'), \
                              environ.get('REMOTE_PORT','-')
        self.command = environ.get('REQUEST_METHOD', '-')

        self.wfile = BytesIO() # for capturing error
        
        try:
            path = self.translate_path(self.path)
            if os.path.isfile(path):
                self._filename = os.path.basename(path)
                etag = '"%s"' % os.path.getmtime(path)
                client_etag = environ.get('HTTP_IF_NONE_MATCH')
                self.send_header('ETag', etag)
                if etag == client_etag:
                    self.send_response(304, "Not Modified")
                    self.start_response(self.status, self.headers)
                    raise StopIteration()
        except OSError:
            pass # Probably a 404

        # for k in environ:
        #    print(k, environ.get(k))

        http_continue = False
        self._m_http_range = ""
        http_range = environ.get("HTTP_RANGE")
        if http_range is not None:
            http_range = http_range.lower()
            self._m_http_range = http_range
            range_list = http_range.split("bytes=")
            if len(range_list) == 2:
                range_list = range_list[1]
                try:
                    start, end = range_list.split('-')
                    start = int(start)
                    if end != "":
                        end = int(end)
                    self.range_start = start
                    self.range_end   = end
                    http_continue = True
                except Exception as e:
                    http_continue = False

        f = self.send_head()
        if f:
            # block_size = 16 * 1024
            # block_size = 4 * 1024 # 5M/S
            # block_size = 256 * 1024 # 9M/S
            total_size = int(self.get_header("Content-Length"))
            self._m_total_size = total_size
            
            block_size = 64 * 1024 # 10M/S
            if http_continue:
                if self.range_end == "":
                    self.range_end = int(total_size-1) # total_size-1, this is ending index

                for buf in self.send_fixed_range(f, block_size):
                    yield buf
                f.close()
                raise StopIteration()

            self.start_response(self.status, self.headers)
            # if total_size > 10 * 1024 ** 2:
            #     buf = f.read(block_size)
            #     print ("%s - - [%s] " % (self.client_address, self.get_date_str()), "first chunk")
            #     yield buf
            #     raise StopIteration()
            while True:
                buf = f.read(block_size)
                if not buf:
                    break
                yield buf
            f.close()
        else:
            # f is None, redirect, @see http.server
            # value = self.wfile.getvalue()
            # yield value
            self.start_response(self.status, self.headers)
            raise StopIteration()

def is_stared(path):
    return config.has_config("STARED_DIRS", path)

def get_filesystem_kw():
    """return filesystem utils"""
    kw = {}
    kw["os"] = os
    kw["is_stared"] = is_stared
    kw["search_type"] = "fs"
    return kw

class MyFileSystemApp(MyStaticApp):

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        words = list(words)
        del words[0] # delete `/fs/`
        path = os.path.sep.join(words)
        if trailing_slash:
            path += '/'
        if os.name == "posix":
            path = "/" + path
        print("PATH:", path)
        return path

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        list.sort(key=lambda a: os.path.isfile(os.path.join(path,a)))
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path,
                                               errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)

        path2 = path.replace("\\", "/")
        if path2.endswith("/"):
            path2 = path[:-1]
        parent_path = os.path.dirname(path2).replace("\\", "/") # fix windows file sep
        path = path.replace("\\", "/")
        kw = get_filesystem_kw()
        kw["filelist"] = list
        kw["path"] = path
        kw["current_path"] = path
        kw["parent_path"] = parent_path

        content = render_template("fs/fs.html", **kw)
        displaypath = xutils.html_escape(displaypath)
        enc = "utf-8"
        encoded = content
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(200, "OK")
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f


class MyStaticMiddleware:
    """WSGI middleware for serving static files."""
    def __init__(self, app, prefix='/fs/'):
        self.app = app
        self.prefix = prefix
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        path = self.normpath(path)

        if path.startswith("/fs/"):
            if path == "/fs/" and xutils.is_windows():
                # can not use web.seeother here
                # handle to webpy handler
                return self.app(environ, start_response)
            return MyFileSystemApp(environ, start_response)
        elif path.startswith("/static/"):
            return MyStaticApp(environ, start_response)
        else:
            return self.app(environ, start_response)

    def normpath(self, path):
        path2 = posixpath.normpath(unquote(path))
        if path.endswith("/"):
            path2 += "/"
        return path2
