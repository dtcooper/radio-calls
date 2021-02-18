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
COPY . /app

CMD ["/bin/sh", "-c", "[ \"${FLASK_ENV}\" = 'production' ] && exec gunicorn -w 3 -b 0.0.0.0:5000 --forwarded-allow-ips '*' --capture-output --enable-stdio-inheritance --log-level=info --access-logfile - --error-logfile - calls:app || exec flask run"]
