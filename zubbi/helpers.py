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

from flask import render_template, request

from .utils import prettydate


def make_error_handler(template="error.html"):
    def _handler(e):
        return (
            render_template(template, error_code=e.code, error_message=e.description),
            e.code,
        )

    return _handler


def current_endpoint(endpoint):
    blueprint_name = request.blueprint
    # Logic from flask.helpers.url_for
    if endpoint[:1] == ".":
        if blueprint_name is not None:
            endpoint = blueprint_name + endpoint
        else:
            endpoint = endpoint[1:]
    return request.endpoint == endpoint


def init_helpers(app):
    app.add_template_test(current_endpoint)
    app.add_template_filter(prettydate)


def calculate_pagination(current_page, last_page, step_size=2):
    start = 0
    end = last_page
    steps = []

    if current_page + step_size < last_page - 1:
        # We have a gap on the end
        end = current_page + step_size

    if current_page > step_size + 1:
        # We have a gap on the start
        start = current_page - step_size
        steps.append([0])

    steps.append([i for i in range(start, end + 1)])

    if end != last_page:
        steps.append([last_page])

    pagination = {"current": current_page, "last_page": last_page, "steps": steps}
    return pagination
