FROM python:3.8-buster

COPY . /app/manager
WORKDIR /app/manager

RUN apt-get update
RUN apt-get install -y build-essential musl-dev gcc g++ libffi-dev libssl-dev python2 python2-dev python3-dev libkrb5-dev libpq-dev \
    && pip install cython \
    && pip install psycopg2-binary \
    && pip3 install -r /app/manager/requirements.txt \
    && rm -rf /var/cache/apk/* \
    && rm -rf /usr/share/man \
    && rm -rf /tmp/*

CMD ["python3", "/app/manager/main.py"]
