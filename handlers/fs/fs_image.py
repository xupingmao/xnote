# encoding=utf-8
import logging
import traceback
import multiprocessing
import xconfig
import os
import sys
import subprocess
import base64

from io import BytesIO
from xutils import cacheutil


def do_create_thumbnail_async(img_path, q):
    """创建缩略图数据,此方法会在子进程中运行"""
    result = do_create_thumbnail_inner(img_path)
    q.put(result)

def do_create_thumbnail_inner(img_path):
    """创建缩略图"""
    im = None
    crop_im = None

    try:
        from PIL import Image
        im = Image.open(img_path)
        w,h = im.size
        
        # 先裁剪成正方形
        width = min(w,h)
        
        start_x = (w-width)//2
        start_y = (h-width)//2
        
        stop_x = start_x + width
        stop_y = start_y + width
        
        region = (start_x,start_y,stop_x,stop_y)
        
        logging.info("File:%s,size:%s,region:%s", img_path, im.size, region)

        crop_im = im.crop(region)
        crop_im.thumbnail((200,200))
        img_bytes = BytesIO()
        crop_im.save(img_bytes, format=im.format)
        return img_bytes.getvalue()
    except:
        traceback.print_exc()
        return None


class ImageCache:

    cache = cacheutil.PrefixedCache("image-cache:")

    @classmethod
    def get(cls, path):
        cls.cache.get(path)

    @classmethod
    def save(cls, path, data):
        cls.cache.put(path, data)


def do_create_thumbnail(path, debug=False):
    q = multiprocessing.Queue()
    if debug:
        return do_create_thumbnail_inner(path)
    else:
        # Windows和Mac不能使用COW的方式创建线程，multiprocessing性能比较差
        args = [sys.executable, "tools/image-thumbnail.py", path]
        with subprocess.Popen(args, stdout=subprocess.PIPE, shell=True) as proc:
            buf = proc.stdout.read()
            if buf == "":
                return None
            return base64.b64decode(buf.decode("utf-8"))

def create_thumbnail_data(path):
    """TODO: 热加载的时候Pickle反序列化会报错"""

    cache_data = ImageCache.get(path)
    if cache_data != None:
        logging.info("hit image cache, path=%s", path)
        return cache_data

    try:
        data = do_create_thumbnail(path)
        if data != None:
            ImageCache.save(path, data)
        return data
    except Exception as e:
        logging.error("image thumbnail data: exception occurs")
        traceback.print_exc()
        return None