
# 目前只适用于Mac本地环境的测试
# 构建最新的css、js文件
source build.sh

rm -rf testdata
echo $(date "+v2.5-dev-%Y.%m.%d") > version.txt

echo 'run test in python-3.4'
/usr/local/bin/python3.4 -m pytest tests --doctest-modules --cov handlers --cov xutils --cov core

echo -e '\n\nrun test in python-3.7'
python3 -m pytest tests --doctest-modules --cov handlers --cov xutils --cov core

echo -e '\n\nrun test in python-2.7'
python2 -m pytest tests --doctest-modules --cov handlers --cov xutils --cov core

# clean test dir
rm -rf testdata
