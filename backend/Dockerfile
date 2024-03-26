FROM python:3.12

ENV DJANGO_SETTINGS_MODULE=calls.settings \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
     && rm -rf /var/lib/apt/lists/*

ARG POETRY_VERSION=1.8.2
RUN wget -qO - https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml poetry.lock /app/
WORKDIR /app
ARG DEV_MODE=0
RUN poetry install $([ -z "$DEV_MODE" -o "$DEV_MODE" = '0' ] && echo '--without=dev') \
    && python -c 'from whisper import _download as d, _MODELS as m; d(m["tiny.en"], "/root/.cache/whisper/", False)'

COPY . /app/

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []
