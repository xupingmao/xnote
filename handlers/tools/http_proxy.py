# encoding=utf-8
# Created by xupingmao on 2017/03/19

import socket
import sys
import threading
import time
import re

config = {
    # 代理监听地址
    "proxy.port": 1222,
    "proxy.host": "localhost",
    # 转发的服务器地址
    "server.port": 1234,
    "server.host": "localhost",
}

sys_print = print

def print(*nargs, **kw):
    thread = threading.current_thread()
    sys_print(time.strftime("%Y-%m-%d %H:%M:%S"), thread.getName(), *nargs, **kw)
    sys.stdout.flush()
    
def sock_init(**config):
    """初始化监听socket"""
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    # TODO 查明两者区别
    s.bind((config["proxy.host"], config["proxy.port"]))
    s.listen(1500)
    return s
    
def sock_copy(from_sock, to_sock, req_addr=None):
    resp = b''
    while 1:
        try:
            buf = from_sock.recv(1024*8)
            if buf:
                # 返回处理结果
                print('send to', req_addr, len(buf))
                to_sock.send(buf)
        except socket.timeout as e:
            print(e)
            break

        if not buf or\
           buf.startswith(b'WebSocket') and buf.endswith(b'\r\n\r\n'):
            break

class ProxyThread(threading.Thread):
    """代理线程"""
    def __init__(self, conn, addr, server_addr):
        super(ProxyThread, self).__init__()
        # self.setDaemon(True)
        self.config = config
        self.server_addr = server_addr
        self.conn = conn
        self.addr = addr

    def run(self):
        try:
            self._run()
        except socket.timeout as e:
            print(e)
        
    def _run(self):
        server_addr = self.server_addr
        conn = self.conn
        addr = self.addr
        
        print(addr)
        headers = b''
        # 接收请求
        while 1:
            buf = conn.recv(2048)
            headers += buf
            if len(buf) < 2048:
                break
        print(headers)
        headers = headers.decode("utf-8")
        # 关闭长连接
        headers = headers.replace('keep-alive', 'close')
        
        # 转发请求
        s1 = socket.socket()
        s1.connect(server_addr)
        # 发送POST数据
        if "Content-Length" in headers:
            # 有一部分数据和headers在同一个数据包里面
            # TODO 需要复习网络数据包的传输
            # 如果已经读完了整个数据包, recv会一直block住
            # 比较小的请求会被合到首部的数据包里面
            data_idx = headers.find("\r\n\r\n")
            data = headers[data_idx+4:]
            content_length = re.findall(r"Content-Length: (\d+)", headers)[0]
            content_length = int(content_length)
            print("Content-Length", content_length)
            print("Data-Length", len(data))
            s1.send(headers.encode("utf-8"))
            size = len(data)
            while size < content_length:
                buf = conn.recv(2048)
                # print(buf)
                size += len(buf)
                s1.send(buf)
        else:
            s1.sendall(headers.encode("utf-8"))

        # 读取结果
        sock_copy(s1, conn, addr)
        conn.close()
    
def main(**config):
    pool = []
    sock = sock_init(**config)
    server_addr = (config["server.host"], config["server.port"])
    while True:
        try:
            conn, addr = sock.accept()
            conn.settimeout(1)
            print(addr)
            # TODO 优化这里的线程池
            thread = ProxyThread(conn, addr, server_addr)
            thread.start()
        except socket.timeout as e:
            print(e)
        # pool.append(thread)

if __name__ == "__main__":
    main(**config)