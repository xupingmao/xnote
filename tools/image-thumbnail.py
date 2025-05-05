# encoding=utf-8
import sys
import logging
import base64
import traceback
import typing

from io import BytesIO

def create_thumbnail(img_path: str, version="v1"):
    """创建缩略图"""

    if version == "v2":
        return create_thumbnail_v2(img_path)

    im = None
    crop_im = None

    try:
        from PIL import Image
        im = Image.open(img_path)
        w,h = im.size
        
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
    

def create_thumbnail_v2(img_path: str):
    """创建缩略图"""
    im = None
    crop_im = None

    try:
        from PIL import Image
        im = Image.open(img_path)
        max_size = (200,200)
        im.thumbnail(max_size)
        img_bytes = BytesIO()
        im.save(img_bytes, format=im.format)
        return img_bytes.getvalue()
    except:
        traceback.print_exc()
        return None

if __name__ == "__main__":
    """参数说明
    image-thumbnail.py path [version]
    """
    path = sys.argv[1]
    version = "v1"
    if len(sys.argv) >= 3:
        version = sys.argv[2]
    data = create_thumbnail(path, version)
    if data != None:
        buf = base64.b64encode(data)
        sys.stdout.write(buf.decode("utf-8"))
    else:
        sys.stdout.write("")