# encoding=utf-8
import logging
import traceback
import multiprocessing

from io import BytesIO

def do_create_thumbnail_data(img_path, q):
    """创建缩略图数据,此方法会在子进程中运行"""
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
        result = img_bytes.getvalue()
        q.put(result)
    except:
        traceback.print_exc()
        q.put(None)

def create_thumbnail_data(path):
    """TODO: 热加载的时候Pickle反序列化会报错"""
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target = do_create_thumbnail_data, args=(path, q))
    p.start()
    p.join(timeout = 0.5)
    try:
        return q.get(False)
    except Exception as e:
        logging.error("image thumbnail data: exception occurs")
        traceback.print_exc()
        return None