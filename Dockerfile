FROM python:3.7.2

COPY requirements.txt ./

RUN pip install --upgrade pip

# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

# set timezone
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone


COPY . .

CMD ["python", "app.py", "--data", "/data", "--port", "5050"]


