FROM python:3.10-slim-buster

LABEL maintainer="sayed1384mahdi@gmail.com"

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY ./bazargan .
