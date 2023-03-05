FROM python:3.11.1-alpine3.17
RUN apk add build-base libpq-dev
COPY ./requirements.txt /requirements.txt
RUN python -m pip install -r /requirements.txt
COPY . /app
WORKDIR /app