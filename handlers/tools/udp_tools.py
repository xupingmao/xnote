# encoding=utf-8
# from socket import *  

# HOST = '192.168.0.10'  
# PORT = 21567  
# BUFSIZE = 1024  

# ADDR = (HOST, PORT)  

# udpCliSock = socket(AF_INET, SOCK_DGRAM)  

# while True:  
#     data = input('>')  
#     if not data:  
#         break  
#     udpCliSock.sendto(bytes(data,encoding='utf-8'),ADDR)  
#     data,ADDR = udpCliSock.recvfrom(BUFSIZE)  
#     if not data:  
#         break  
#     print (data)  # data is byte

# udpCliSock.close()

import socket
import threading
import sys

def log(*args):
    print(*args)
    sys.stdout.flush()

class UdpServer(threading.Thread):

    def __init__(self, host, port):
        super(UdpServer, self).__init__()
        self.host = host
        self.port = port

    def run(self):
        log("Listen at", self.port)
        buf_size = 1024
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind((self.host, self.port))
        while True:
            data, addr = server.recvfrom(buf_size)
            log("recv from %s, %s bytes" % (addr, len(data)))

if __name__ == '__main__':
    server = UdpServer("0.0.0.0", 45655)
    server.start()



