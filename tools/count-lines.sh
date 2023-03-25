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
cloc ./ --fullpath --not-match-d="py3.8|py3.7|py3.6|lib|static/lib|data|htmlcov"