from __future__ import print_function

import sys, os
import urllib
import posixpath
import time

from . import webapi as web
from . import net
from . import utils
from .py3helpers import PY2

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

__all__ = ["runsimple"]

def runbasic(func, server_address=("0.0.0.0", 8080)):
    """
    Runs a simple HTTP server hosting WSGI app `func`. The directory `static/` 
    is hosted statically.

    Based on [WsgiServer][ws] from [Colin Stewart][cs].
    
  [ws]: http://www.owlfish.com/software/wsgiutils/documentation/wsgi-server-api.html
  [cs]: http://www.owlfish.com/
    """
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

    import SocketServer
    import socket, errno
    import traceback

    class WSGIHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def run_wsgi_app(self):
            protocol, host, path, parameters, query, fragment = \
                urlparse.urlparse('http://dummyhost%s' % self.path)

            # we only use path, query
            env = {'wsgi.version': (1, 0)
                   ,'wsgi.url_scheme': 'http'
                   ,'wsgi.input': self.rfile
                   ,'wsgi.errors': sys.stderr
                   ,'wsgi.multithread': 1
                   ,'wsgi.multiprocess': 0
                   ,'wsgi.run_once': 0
                   ,'REQUEST_METHOD': self.command
                   ,'REQUEST_URI': self.path
                   ,'PATH_INFO': path
                   ,'QUERY_STRING': query
                   ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
                   ,'CONTENT_LENGTH': self.headers.get('Content-Length', '')
                   ,'REMOTE_ADDR': self.client_address[0]
                   ,'SERVER_NAME': self.server.server_address[0]
                   ,'SERVER_PORT': str(self.server.server_address[1])
                   ,'SERVER_PROTOCOL': self.request_version
                   }

            for http_header, http_value in self.headers.items():
                env ['HTTP_%s' % http_header.replace('-', '_').upper()] = \
                    http_value

            # Setup the state
            self.wsgi_sent_headers = 0
            self.wsgi_headers = []

            try:
                # We have there environment, now invoke the application
                result = self.server.app(env, self.wsgi_start_response)
                try:
                    try:
                        for data in result:
                            if data: 
                                self.wsgi_write_data(data)
                    finally:
                        if hasattr(result, 'close'): 
                            result.close()
                except socket.error as socket_err:
                    # Catch common network errors and suppress them
                    if (socket_err.args[0] in \
                       (errno.ECONNABORTED, errno.EPIPE)): 
                        return
                except socket.timeout as socket_timeout: 
                    return
            except:
                print(traceback.format_exc(), file=web.debug)

            if (not self.wsgi_sent_headers):
                # We must write out something!
                self.wsgi_write_data(" ")
            return

        do_POST = run_wsgi_app
        do_PUT = run_wsgi_app
        do_DELETE = run_wsgi_app

        def do_GET(self):
            if self.path.startswith('/static/'):
                SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.run_wsgi_app()

        def wsgi_start_response(self, response_status, response_headers, 
                              exc_info=None):
            if (self.wsgi_sent_headers):
                raise Exception \
                      ("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgi_headers = (response_status, response_headers)
            return self.wsgi_write_data

        def wsgi_write_data(self, data):
            if (not self.wsgi_sent_headers):
                status, headers = self.wsgi_headers
                # Need to send header prior to data
                status_code = status[:status.find(' ')]
                status_msg = status[status.find(' ') + 1:]
                self.send_response(int(status_code), status_msg)
                for header, value in headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wsgi_sent_headers = 1
            # Send the data
            self.wfile.write(data)

    class WSGIServer(SocketServer.ThreadingMixIn, HTTPServer):
        def __init__(self, func, server_address):
            HTTPServer.HTTPServer.__init__(self, 
                                               server_address, 
                                               WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    print("http://%s:%d/" % server_address)
    WSGIServer(func, server_address).serve_forever()

# The WSGIServer instance. 
# Made global so that it can be stopped in embedded mode.
server = None

def runsimple(func, server_address=("0.0.0.0", 8080)):
    """
    Runs [CherryPy][cp] WSGI server hosting WSGI app `func`. 
    The directory `static/` is hosted statically.

    [cp]: http://www.cherrypy.org
    """
    global server
    func = StaticMiddleware(func)
    func = LogMiddleware(func)
    
    server = WSGIServer(server_address, func)

    if server.ssl_adapter:
        print("https://%s:%d/" % server_address)
    else:
        print("http://%s:%d/" % server_address)

    try:
        server.start()
    except (KeyboardInterrupt, SystemExit):
        server.stop()
        server = None

def WSGIServer(server_address, wsgi_app):
    """Creates CherryPy WSGI server listening at `server_address` to serve `wsgi_app`.
    This function can be overwritten to customize the webserver or use a different webserver.
    """
    from . import wsgiserver
    
    # Default values of wsgiserver.ssl_adapters uses cherrypy.wsgiserver
    # prefix. Overwriting it make it work with web.wsgiserver.
    wsgiserver.ssl_adapters = {
        'builtin': 'web.wsgiserver.ssl_builtin.BuiltinSSLAdapter',
        'pyopenssl': 'web.wsgiserver.ssl_pyopenssl.pyOpenSSLAdapter',
    }
    
    server = wsgiserver.CherryPyWSGIServer(server_address, wsgi_app, server_name="localhost")
        
    def create_ssl_adapter(cert, key):
        # wsgiserver tries to import submodules as cherrypy.wsgiserver.foo.
        # That doesn't work as not it is web.wsgiserver. 
        # Patching sys.modules temporarily to make it work.
        import types
        cherrypy = types.ModuleType('cherrypy')
        cherrypy.wsgiserver = wsgiserver
        sys.modules['cherrypy'] = cherrypy
        sys.modules['cherrypy.wsgiserver'] = wsgiserver
        
        from wsgiserver.ssl_pyopenssl import pyOpenSSLAdapter
        adapter = pyOpenSSLAdapter(cert, key)
        
        # We are done with our work. Cleanup the patches.
        del sys.modules['cherrypy']
        del sys.modules['cherrypy.wsgiserver']

        return adapter

    # SSL backward compatibility
    if (server.ssl_adapter is None and
        getattr(server, 'ssl_certificate', None) and
        getattr(server, 'ssl_private_key', None)):
        server.ssl_adapter = create_ssl_adapter(server.ssl_certificate, server.ssl_private_key)

    server.nodelay = not sys.platform.startswith('java') # TCP_NODELAY isn't supported on the JVM
    return server

class StaticApp(SimpleHTTPRequestHandler):
    """WSGI application for serving static files."""
    def __init__(self, environ, start_response):
        self.headers = []
        self.environ = environ
        self.start_response = start_response

    def send_response(self, status, msg=""):
        #the int(status) call is needed because in Py3 status is an enum.IntEnum and we need the integer behind
        self.status = str(int(status)) + " " + msg

    def send_header(self, name, value):
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

        self.send_header("Content-Range", content_range)
        self.send_header("Content-Length", content_length)
        # self.send_header("Content-Type", "application/octet-stream")
        self.send_response(206,"Partial Content")
        # self.send_response(200, "OK")
        self.start_response(self.status, self.headers)

        while start <= end:
            rest_size = end - start + 1
            size = block_size
            if rest_size < block_size:
                size = rest_size
            buf = f.read(size)
            start += size
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
            etag = '"%s"' % os.path.getmtime(path)
            client_etag = environ.get('HTTP_IF_NONE_MATCH')
            self.send_header('ETag', etag)
            if etag == client_etag:
                self.send_response(304, "Not Modified")
                self.start_response(self.status, self.headers)
                raise StopIteration()
        except OSError:
            pass # Probably a 404

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
                if self.range_end != "":
                    for buf in self.send_fixed_range(f, block_size):
                        yield buf
                    f.close()
                    raise StopIteration()
                buf = self.send_range(f, block_size)
                yield buf
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
            value = self.wfile.getvalue()
            yield value

class StaticMiddleware:
    """WSGI middleware for serving static files."""
    def __init__(self, app, prefix='/static/'):
        self.app = app
        self.prefix = prefix
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        path = self.normpath(path)

        if path.startswith(self.prefix):
            return StaticApp(environ, start_response)
        else:
            return self.app(environ, start_response)

    def normpath(self, path):
        path2 = posixpath.normpath(unquote(path))
        if path.endswith("/"):
            path2 += "/"
        return path2

    
class LogMiddleware:
    """WSGI middleware for logging the status."""
    def __init__(self, app):
        self.app = app
        self.format = '%s - - [%s] "%s %s %s" - %s'
    
        f = BytesIO()
        
        class FakeSocket:
            def makefile(self, *a):
                return f
        
        # take log_date_time_string method from BaseHTTPRequestHandler
        self.log_date_time_string = BaseHTTPRequestHandler(FakeSocket(), None, None).log_date_time_string
        
    def __call__(self, environ, start_response):
        def xstart_response(status, response_headers, *args):
            out = start_response(status, response_headers, *args)
            self.log(status, environ)
            return out

        return self.app(environ, xstart_response)
             
    def log(self, status, environ):
        outfile = environ.get('wsgi.errors', web.debug)
        req = environ.get('PATH_INFO', '_')
        protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
        method = environ.get('REQUEST_METHOD', '-')
        host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                          environ.get('REMOTE_PORT','-'))

        time = self.log_date_time_string()

        msg = self.format % (host, time, protocol, method, req, status)
        print(utils.safestr(msg), file=outfile)
