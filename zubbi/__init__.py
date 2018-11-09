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

import os

from flask import Blueprint, Flask

from . import default_settings
from .helpers import init_helpers, make_error_handler
from .models import init_elasticsearch
from .views import (
    AutoCompleteView,
    DetailView,
    HowToView,
    IndexView,
    LmzifyView,
    SearchView,
    WebhookView,
)


class ZubbiBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        IndexView.register_url(self)
        SearchView.register_url(self)
        DetailView.register_url(self)
        HowToView.register_url(self)
        AutoCompleteView.register_url(self)
        WebhookView.register_url(self)
        LmzifyView.register_url(self)

        self.record(self._init_blueprint)
        self.record_once(self._init_blueprint_once)

    def _init_blueprint(self, state):
        for key in dir(default_settings):
            if key.isupper():
                state.app.config.setdefault(key, getattr(default_settings, key))
        init_helpers(state.app)

    def _init_blueprint_once(self, state):
        init_elasticsearch(state.app)


blueprint = ZubbiBlueprint(
    "zubbi", __name__, template_folder="templates", static_folder="static"
)


ZUBBI_SETTINGS_ENV = "ZUBBI_SETTINGS"


def create_app(config=None):
    app = Flask(__name__)

    if config is None:
        app.config.from_envvar(ZUBBI_SETTINGS_ENV)
    else:
        app.config.from_mapping(config)

    app.register_blueprint(blueprint)

    error_handler = make_error_handler()

    app.register_error_handler(400, error_handler)
    app.register_error_handler(404, error_handler)

    try:
        os.makedirs(app.instance_path)
    except FileExistsError:
        pass

    return app
