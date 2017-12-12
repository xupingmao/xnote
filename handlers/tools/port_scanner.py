# encoding=utf-8

import socket 
import sys
import threading
import multiprocessing 

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

PY2 = sys.version_info[0] == 2

if not PY2:
    xrange = range


class TextImage:

    def __init__(self):
        self.last = ''

    def update(self, msg):
        with _lock:
            self.clear_message(len(self.last))
            self.print_message(msg)
            self.last = msg

    def print_message(self, msg):
        with _lock:
            # 使用print没有效果
            sys.stdout.write(msg)
            sys.stdout.flush()

    def clear_message(self, length):
        if length == 0:
            return
        back = '\b' * length
        whitespace = '\b' * length
        sys.stdout.write(back)
        sys.stdout.write(whitespace)
        sys.stdout.write(back)
        sys.stdout.flush()

def scan(addr, port, img): 
    s = socket.socket() 
    s.settimeout(0.01) 
    if s.connect_ex((addr, port)) == 0: 
        img.update('%s is open\n' % port)
    s.close() 

_lock = threading.RLock()
_handled = 0
 
def worker(addr, q, total):
    global _lock 
    global _handled
    img = TextImage()
    while not q.empty(): 
        port = q.get() 
        # print("process %s" % port)
        try: 
            img.update("%d/%d" % (_handled, total))
            scan(addr, port, img) 
        finally: 
            with _lock:
                _handled += 1
            # q.task_done() 
 
if __name__ == '__main__': 
    addr  = sys.argv[1]
    start = int(sys.argv[2])
    end   = int(sys.argv[3])
    print("scan %s-%s" % (start, end))
    q = Queue() 
    # map(q.put,xrange(1,65535)) 
    total = 0
    for port in range(start, end+1):
        q.put(port)
        total += 1
    # jobs = [multiprocessing.Process(target=worker, args=(q,total)) for i in range(100)] 
    jobs = [threading.Thread(target=worker, args=(addr, q, total)) for i in range(10)]
    for job in jobs:
        job.start()
    # map(lambda x:x.start(),jobs)


