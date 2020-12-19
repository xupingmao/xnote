FROM python:3.7.2

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py", "--data", "/data", "--port", "5050"]


