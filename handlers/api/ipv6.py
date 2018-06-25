# encoding=utf-8
# Created by xupingmao on 2016/03/24
# @modified 2018/06/26 01:04:13
import re
import subprocess
import xutils

def cal_ipv6_address():
    """
	Get local ipv6
    """
    pageURL='http://ipv6.bupt.edu.cn/cgi-bin/showip.pl'
    content=urllib2.urlopen(pageURL).read()

    ipv6_pattern='(([a-f0-9]{1,4}:){7}[a-f0-9]{1,4})'
    
    m = re.search(ipv6_pattern, content)
    
    if m is not None:
        return m.group()
    else:
        return None

def get_local_ipv6_address():
    """
    This function will return your local machine's ipv6 address if it exits.
    If the local machine doesn't have a ipv6 address,then this function return None.
    This function use subprocess to execute command "ipconfig", then get the output
    and use regex to parse it ,trying to  find ipv6 address.
    """
    if xutils.is_windows():
        getIPV6_process = subprocess.Popen("ipconfig", stdout = subprocess.PIPE)
    elif xutils.is_mac():
        getIPV6_process = subprocess.Popen("ifconfig", stdout = subprocess.PIPE)
    else:
        getIPV6_process = None
    
    if not getIPV6_process:
        return None

    output = (getIPV6_process.stdout.read())
    getIPV6_process.stdout.close()

    ipv6_pattern='(([a-f0-9]{1,4}:){7}[a-f0-9]{1,4})'
    m = re.search(ipv6_pattern, str(output))
    if m is not None:
        return m.group()
    else:
        return None

class handler:
    def GET(self):
        return get_local_ipv6_address()

