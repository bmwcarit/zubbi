# NOTE: This Dockerfile should only be used for demonstration purposes and not
# in a production system. Flask is running in development mode and listens on
# all public IPs to make it reachable from outside the docker container.
FROM alpine:3.9

WORKDIR /opt

RUN apk add --no-cache openssl-dev curl zeromq git python3

# Packages needed to build the cffi python package which is needed by cryptography
RUN apk add --no-cache --virtual .build-deps \
        libffi-dev \
        build-base \
        python3-dev \
    # Install zubbi from PyPI
    && pip3 install --no-cache zubbi \
    # Delete build dependencies
    && apk del .build-deps

COPY settings.cfg tenant-config.yaml ./

VOLUME /opt/instance

ENV ZUBBI_INSTANCE_PATH=/opt/instance
ENV ZUBBI_SETTINGS=/opt/settings.cfg
ENV FLASK_APP=zubbi

# flask runs on port 5000 per default
EXPOSE 5000

# NOTE (fschmidt): The --host option is necessary, to reach flask from outside
# the docker container
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
