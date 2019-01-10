FROM alpine:3.7

WORKDIR /opt

RUN apk add --no-cache openssl-dev curl zeromq git python3

COPY settings.cfg tenant-config.yaml ./

# Packages needed to build the cffi python package which is needed by cryptography
RUN apk add --no-cache --virtual .build-deps \
        libffi-dev \
        build-base \
        python3-dev \
    && pip3 install --no-cache zubbi \
    && apk del .build-deps

VOLUME /opt/instance
VOLUME /var/share/zubbi

ENV ZUBBI_INSTANCE_PATH=/opt/instance
ENV ZUBBI_SETTINGS=/opt/settings.cfg
ENV FLASK_APP=zubbi
# flask runs on port 5000 per default
#EXPOSE 5000

# NOTE (fschmidt): The --host option is necessary, to reach flask from outside
# the docker container
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
