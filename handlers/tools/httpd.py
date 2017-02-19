#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import codecs
import socket
import logging
from urllib.parse import unquote

from io import StringIO

PORT = 8080
HOST = '30.15.53.146'
PORT = 1234

localIp = socket.gethostbyname(socket.gethostname())
HOST = localIp 
ipList = socket.gethostbyname_ex(socket.gethostname())
realIpList = []
for ipl in ipList[:]:
    if not isinstance(ipl, list):
        pass
    elif len(ipl)==0:
        pass
    else:
        realIpList = ipl
for i in ipList:
    if i != localIp:
       print("external IP:%s"%i)

HOST = realIpList[0]

#Read index.html, put into HTTP response data
index_content = '''
HTTP/1.x 200 OK
Content-Type: text/html

'''

response_header = '''HTTP/1.1 200 OK\r\nServer: Tengine\r\nDate: Mon, 17 Aug 2015 09:43:10 GMT\r\nContent-Type: text/html;charset=UTF-8\r\nConnection: close\r\n'''

def url_escape(url):
    # url = url.replace("%20", " ")
    return unquote(url)


logger = None

def LOG(*args):
    global logger
    if logger == None:
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler("logger.log")
        # 设置日志格式
        handler.setFormatter(logging.Formatter(fmt="%(asctime)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)

    print(time.strftime('%Y-%m-%d %H:%M:%S'), *args)
    logger.error(args)


def sock_recv(conn, size):
    try:
        buf = conn.recv(8192) # 8K
        # LOG(request)
        return buf
    except ConnectionResetError as e:
        LOG('connection was closed by remote server')
    except Exception as e:
        LOG(e)
    return None
    
def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.setdefaulttimeout(1)
    sock.bind((HOST, PORT))
    sock.listen(100) # maximum number of requests waiting
    print('server start at %s:%s ...' % (HOST, PORT))
    #infinite loop
    while True:
        conn, addr = sock.accept()
        originRequest = sock_recv(8192); # 8K
        if originRequest is None:
            continue
        request = codecs.decode(originRequest, "utf-8")
        if not request:
            LOG('disconnect from', addr)
            continue
        blocks = request.split(' ')
        method = blocks[0]
        url = blocks[1]
        content = request
        LOG(method, url)
        LOG(request)
        if method.upper() == "POST":
            req = sock_recv(conn, 10000)
            LOG(req)
        # content = codecs.encode(content, "byte")
        # so sendall can send bytes. ^_^;
        try:
            conn.sendall(codecs.encode(
                    '''HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n''', 'utf-8'))
            if isinstance(content, str):
                content = codecs.encode(content, "utf-8")
            conn.sendall(content)
            conn.close()
        except ConnectionAbortedError as e:
            LOG("connection closed by client")


if __name__ == '__main__':
    try:
        start_server()
    except:
        input("exception")