FROM python:3.9-alpine3.13
LABEL maintainer="parkermedl.in"

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /requirements.txt
COPY ./app /app
COPY ./scripts /scripts
COPY ./whls /whls
COPY ./init_db_imports /init_db_imports

WORKDIR /app
EXPOSE 8000
EXPOSE 5342

RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    apk add --update --no-cache postgresql-client && \
    apk add --update --no-cache --virtual .tmp-deps \
        build-base postgresql-dev musl-dev linux-headers && \
    /py/bin/pip install -r /requirements.txt && \
    apk del .tmp-deps && \
    adduser --disabled-password --no-create-home app && \
    mkdir -p /vol/web/static && \
    mkdir -p /vol/web/media && \
    chown -R app:app /vol && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts && \
    apk add tree

ENV PATH="/scripts:/py/bin:$PATH"

USER app

# I don't think we need this CMD because I handle the stuff in run.sh 
# using a command in the docker-compose file. Leaving it in a comment 
# here so I don't forget how to do this. 

# CMD ["run.sh"]