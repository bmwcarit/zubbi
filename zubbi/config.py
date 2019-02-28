# Copyright 2018 BMW Car IT GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from os import environ

from . import default_settings


ENVIRONMENT_VARIABLES_AVAILABLE = [
    "CONNECTIONS",
    "ES_HOST",
    "ES_USERNAME",
    "ES_PASSWORD",
    "ES_PORT",
    "FORCE_SCRAPE_INTERVAL",
    "GITHUB_WEBHOOK_ADDRESS",
    "SEARCH_BATCH_SIZE",
    "SEARCH_BATCH_LIMIT",
    "TENANT_SOURCES_FILE",
    "ZMP_SUB_SOCKET_ADDRESS",
    "ZMP_PUB_SOCKET_ADDRESS",
    "ZMQ_SUB_TIMEOUT",
]

LOGGER = logging.getLogger(__name__)


def init_configuration(config):
    _default_configuration(config)
    _environment_configuration(config)


def _default_configuration(config):
    for key in dir(default_settings):
        if key.isupper():
            config.setdefault(key, getattr(default_settings, key))


def _environment_configuration(config):
    for key in ENVIRONMENT_VARIABLES_AVAILABLE:
        if key in environ:
            config[key] = environ.get(key)
            LOGGER.warning("  -> The key %s is overrided by environment", key)
