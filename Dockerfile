FROM python:3.7.2

COPY config/requirements.txt ./

RUN pip config set global.cache-dir "/data/pip-cache"

RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# install required packages
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# set timezone
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone


COPY . /home

WORKDIR /home

CMD ["python", "sentinel.py", "app.py", "--config", "config/boot/boot.sae.properties"]

