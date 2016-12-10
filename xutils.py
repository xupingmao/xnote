from web.py3helpers import PY2

if PY2:
    from urllib import quote, unquote, urlopen
else:
    from urllib.parse import quote, unquote
    from urllib.request import urlopen