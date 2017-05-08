# encoding=utf-8
# Created by xupingmao on 2017/05/05
import time
import sys

class TextImage:

    def __init__(self):
        self.last = ''

    def update(self, msg):
        self.clear_message(len(self.last))
        self.print_message(msg)
        self.last = msg

    def print_message(self, msg):
        # 使用print没有效果
        sys.stdout.write(msg)
        sys.stdout.flush()

    def clear_message(self, length):
        back = '\b' * length
        whitespace = '\b' * length
        # sys.stdout.write('\0')
        sys.stdout.write(back)
        sys.stdout.write(whitespace)
        sys.stdout.write(back)
        sys.stdout.flush()

def main():
    img = TextImage()
    while True:
        # msg = "*" * 30 + "\n"
        # msg += time.ctime() + "\n"
        # msg += "*" * 30
        img.update(time.ctime())
        time.sleep(0.1)


if __name__ == '__main__':
    main()