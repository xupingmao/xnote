###
 # @Author       : xupingmao
 # @email        : 578749341@qq.com
 # @Date         : 2022-02-07 12:35:20
 # @LastEditors  : xupingmao
 # @LastEditTime : 2023-03-25 23:03:06
 # @FilePath     : /xnote/tools/count-lines.sh
 # @Description  : 描述
### 
# Mac安装: brew install cloc

import os
import sys

# print(sys.path)
if "./" not in sys.path:
    sys.path.insert(0, "./")

from xutils import osutil

def main():
    if osutil.is_command_exists("cloc"):
        command = 'cloc ./ --fullpath --not-match-d="py3.8|py3.7|py3.6|lib|static/lib|data|htmlcov"'
        os.system(command)
    else:
        print("cloc command not found, use duck-rush code-count-lines command")
        os.system("code-count-lines xnote handlers xutils xnote_migrate static/js/ --exclude py3.8 py3.7 py3.6 lib static/lib data* htmlcov dist build tmp *.build.js")

if __name__ == "__main__":
    main()

