FROM python:3.8-buster

RUN apt-get update && \
  apt-get install -y build-essential musl-dev gcc g++ libffi-dev libssl-dev libkrb5-dev libpq-dev \
    && pip install cython \
    && pip install psycopg2-binary \
    && rm -rf /var/cache/apk/* \
    && rm -rf /usr/share/man \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . /app/manager/
WORKDIR /app/manager

RUN pip3 install -r /app/manager/requirements.txt

CMD ["python3", "/app/manager/main.py"]
