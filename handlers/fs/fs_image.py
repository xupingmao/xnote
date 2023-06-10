# encoding=utf-8
import logging
import traceback
import sys
import subprocess
import base64
import xconfig
import os

from io import BytesIO
from xutils import cacheutil

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
    if debug:
        return do_create_thumbnail_inner(path)
    else:
        logging.info("path=%s", path)
        # multiprocessing在Windows和Mac的性能比较差，因为他们默认使用新线程而不是fork的方式创建线程，
        script_path = os.path.join(xconfig.FileConfig.source_root_dir, "tools/image-thumbnail.py")
        args = [sys.executable, script_path, path]
        with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
            assert proc.stdout != None
            buf = proc.stdout.read()
            if buf.strip() == "":
                return None
            return base64.b64decode(buf.decode("utf-8"))

def create_thumbnail_data(path):
    cache_data = ImageCache.get(path)
    if cache_data != None:
        logging.info("hit image cache, path=%s", path)
        return cache_data

    try:
        # SAE上处理PIL存在泄漏，暂时先通过子进程处理
        data = do_create_thumbnail(path)
        if data != None:
            ImageCache.save(path, data)
        return data
    except Exception as e:
        logging.error("image thumbnail data: exception occurs")
        traceback.print_exc()
        return None