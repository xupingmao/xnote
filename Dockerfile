FROM python:3.7.2

COPY config/requirements.txt ./

RUN pip install --upgrade pip

# install required packages
RUN pip install -r requirements.txt

# set timezone
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone


COPY . .

CMD ["python", "sentinel.py", "app.py", "--data", "/data", "--port", "5050", "--forceHttps", "yes", "--debug", "no", "--block_cache_size", "1"]


