<!--
 * @Author       : xupingmao
 * @email        : 578749341@qq.com
 * @Date         : 2023-10-15 19:48:02
 * @LastEditors  : xupingmao
 * @LastEditTime : 2023-10-15 20:47:36
 * @FilePath     : /xnote/docs/upload_to_pip.md
 * @Description  : 描述
-->
# 上传到pip

1. 修改setup.py的版本
2. 执行`python setup.py sdist`
3. 安装twine, `python -m pip install twine`
4. 执行`python -m twine upload dist/*`
