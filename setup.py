# encoding=utf-8

import setuptools

with open("README.md", "r", encoding="utf-8") as fp:
    long_description = fp.read()


data_ext_list =  ["*.txt", "*.json", "*.properties", "*.js", "*.html", "*.css"]

setuptools.setup(
    name = "xnote-web",
    version = "0.1.1",
    author = "mark",
    author_email = "578749341@qq.com",
    description = "xnote-web框架",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    # packages = ["config", "core", "docs", "handlers", "lib", "static", "tools", "xnote", "xutils"],
    packages=setuptools.find_packages(),
    include_package_data=True, # 包含资源文件
    # package_dir={"": "."},
    # package_data={
    #     "": data_ext_list,
    #     "handlers": data_ext_list,
    # },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
