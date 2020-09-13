FROM python:3.7-alpine3.9

COPY . /app
WORKDIR /app

RUN apk add --no-cache build-base musl-dev gcc g++ openssl-dev libffi-dev \
    && pip3 install -r /app/requirements.txt \
    && apk del build-base musl-dev gcc g++ openssl-dev \
    && rm -rf /var/cache/apk/* \
    && rm -rf /usr/share/man \
    && rm -rf /tmp/*

CMD ["python3", "/app/main.py"]
