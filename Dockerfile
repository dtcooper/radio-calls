FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV FLASK_ENV development
ENV FLASK_APP calls
ENV FLASK_RUN_HOST 0.0.0.0

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/

RUN pip install -r requirements.txt
