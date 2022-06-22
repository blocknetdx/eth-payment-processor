# docker build -t blocknetdx/eth-payment-processor:latest .
FROM python:3.8-slim-buster

RUN apt-get update && \
  apt-get install -y build-essential musl-dev gcc g++ libffi-dev libssl-dev libkrb5-dev libpq-dev \
    && pip install cython \
    && pip install psycopg2-binary \
    && rm -rf /var/cache/apk/* \
    && rm -rf /usr/share/man \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt /app/manager/requirements.txt
RUN pip3 install -r /app/manager/requirements.txt

COPY . /app/manager/
WORKDIR /app/manager

CMD python3 migrate_db.py && python3 /app/manager/payment_processor.py
