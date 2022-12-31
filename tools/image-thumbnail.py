# encoding=utf-8
import sys
import logging
import base64
import traceback
from io import BytesIO

def create_thumbnail(img_path):
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

if __name__ == "__main__":
    path = sys.argv[1]
    data = create_thumbnail(path)
    if data != None:
        buf = base64.b64encode(data)
        sys.stdout.write(buf.decode("utf-8"))