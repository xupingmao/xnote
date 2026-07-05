from xnote.webui import TabBox

class TabConfig:

    # 编解码工具
    encode_tab = TabBox(tab_key="tab", tab_default="base64", css_class="btn-style")
    encode_tab.add_item(title="BASE64", value="BASE64", href="/tools/encode?tab=BASE64&type=base64")
    encode_tab.add_item(title="BASE32", value="BASE32", href="/tools/encode?tab=BASE32&type=base32")
    encode_tab.add_item(title="BASE62", value="BASE62", href="/tools/encode?tab=BASE62&type=base62")
    encode_tab.add_item(title="16进制转换", value="hex", href="/tools/hex?tab=hex")
    encode_tab.add_item(title="URL编解码", value="urlcoder", href="/tools/urlcoder?tab=urlcoder")
    encode_tab.add_item(title="MD5", value="MD5", href="/tools/hash?tab=MD5&type=md5")
    encode_tab.add_item(title="SHA1", value="SHA1", href="/tools/hash?tab=SHA1&type=sha1")
    encode_tab.add_item(title="SHA256", value="SHA256", href="/tools/hash?tab=SHA256&type=sha256")
    encode_tab.add_item(title="SHA512", value="SHA512", href="/tools/hash?tab=SHA512&type=sha512")
    encode_tab.add_item(title="条形码", value="barcode", href="/tools/barcode?tab=barcode")
    encode_tab.add_item(title="二维码", value="qrcode", href="/tools/qrcode?tab=qrcode")

    # 文本工具
    text_tab = TabBox(tab_key="tab", tab_default="convert", css_class="btn-style")
    text_tab.add_item(title="文本转换", value="convert", href="/tools/text_convert?tab=convert")
    text_tab.add_item(title="文本对比", value="diff", href="/tools/text_diff?tab=diff")
    text_tab.add_item(title="集合运算", value="set", href="/tools/text_set?tab=set")
    text_tab.add_item(title="随机文本", value="random", href="/tools/text_random?tab=random")


    # 图片工具
    img_tab = TabBox(tab_key="tab", tab_default="img_split", css_class="btn-style")
    img_tab.add_item(title="图片合并", value="merge", href="/tools/img_merge?tab=merge")
    img_tab.add_item(title="图片拆分", value="split", href="/tools/img_split?tab=split")
    img_tab.add_item(title="图片灰度", value="gray", href="/tools/img_gray?tab=gray")
    
