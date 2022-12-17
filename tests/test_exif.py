# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-11-13 16:19:54
@LastEditors  : xupingmao
@LastEditTime : 2022-11-26 20:30:06
@FilePath     : /xnote/tests/test_exif.py
@Description  : 描述
"""
# import exifread

# fpath = r"D:\projects\xnote\data\files\admin\gallery\84\00000001664750772084\微信图片_20221113143920.jpg"
# fpath = r"D:\projects\xnote\data\files\admin\upload\2022\11\微信图片_20221113143920_6.jpg"

# with open(fpath, "rb") as fp:
#     tags = exifread.process_file(fp)
#     # print(tags)
#     for tag in tags.keys():
#         print("Key: {0}, Value: {1}".format(tag, tags[tag]))

import os
try:
    import PIL
    from PIL import Image
    from PIL import ExifTags
except ImportError:
    PIL = None


if PIL != None:
    # Pillow 文档 https://pillow.readthedocs.io/en/stable/
    fpath = r"/Users/xupingmao/Downloads/mmexport1668347065669.jpg"
    fpath_new = fpath + "_fixed.jpg"

    tag_orientation = 0x112
    Image.init()

    print(os.path.splitext(fpath))
    print("SAVE_ALL", Image.SAVE_ALL)
    print("SAVE", Image.SAVE)
    print("_plugins", Image._plugins)

def do_fix():
    if PIL == None:
        return
    with Image.open(fpath) as img:
        exif = img.getexif()
        print(exif)
        orientation = exif.get(tag_orientation)
        print("orientation", orientation)

        if orientation == 3:
            img_new = img.copy()
            exif_new = img_new.getexif()
            exif_new[tag_orientation] = 1
            img_new.save(fpath_new)
            img_new.show()
            img_new.close()

# do_fix()