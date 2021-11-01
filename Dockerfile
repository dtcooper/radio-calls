FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=development \
    FLASK_APP=calls \
    FLASK_RUN_HOST=0.0.0.0

ARG POETRY_VERSION=1.1.11

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

RUN mkdir /app
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN poetry install
COPY . /app

CMD ["/bin/sh", "-c", "[ \"${FLASK_ENV}\" = 'production' ] && exec poetry run gunicorn -w 3 -b 0.0.0.0:5000 --forwarded-allow-ips '*' --capture-output --enable-stdio-inheritance --log-level=info --access-logfile - --error-logfile - --access-logformat '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\"' calls:app || exec poetry run flask run"]
