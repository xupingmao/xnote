<!--
 * @Author       : xupingmao
 * @email        : 578749341@qq.com
 * @Date         : 2023-10-15 19:48:02
 * @LastEditors  : xupingmao
 * @LastEditTime : 2024-03-16 18:20:49
 * @FilePath     : /xnote/docs/upload_to_pip.md
 * @Description  : 描述
-->
# 上传到pip

1. 修改setup.py的版本
2. 执行`python setup.py sdist`
3. 安装twine, `python -m pip install twine`
4. 上传文件
    1. 执行`python -m twine upload --username __token__ --password <your-token> dist/*`
    2. 找到你的token,如果没有token,打开[pypi](https://pypi.org/manage/account/) 账号设置,找到API tokens,创建一个新的token,注意这里只会展示一次,需要自己保存下来 (token是`pypi-`开头的很长的字符串)
    3. 输入token,确定后开始上传文件包

