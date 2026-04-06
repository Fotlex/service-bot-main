FROM python:3.13

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "/app"

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
