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

import abc
import hashlib
import hmac
import json
import math

from elasticsearch_dsl import Q
from flask import (
    abort,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.views import MethodView

from .extensions import get_zmq_socket
from .helpers import calculate_pagination
from .models import block_type, BlockSearch, class_from_block_type
from .utils import get_version

SEARCHABLE_FIELDS = frozenset(["name", "description", "tenants", "repo"])
DEFAULT_SEARCH_FIELDS = frozenset(["name", "description"])
SEARCHABLE_BLOCK_TYPES = frozenset(["job", "role"])

WEBHOOK_EVENTS = ["installation", "installation_repositories", "push"]


def json_abort(status, msg=None):
    response = {"error": status}
    if msg is not None:
        response["msg"] = msg
    abort(make_response(jsonify(response), status))


class ZubbiMethodView(MethodView):
    @property
    @abc.abstractmethod
    def endpoint(self):
        pass

    @property
    @abc.abstractmethod
    def rule(self):
        pass

    @property
    @abc.abstractmethod
    def template_name(self):
        pass

    @classmethod
    def register_url(cls, app, **options):
        app.add_url_rule(cls.rule, view_func=cls.as_view(cls.endpoint), **options)

    def get_context(self, **kwargs):
        # Initialize context with meta fields that should be available on all pages
        context = {"meta": {"version": get_version()}}

        # Add additionally provided kwargs
        context = {**context, **kwargs}
        return context


class IndexView(ZubbiMethodView):

    endpoint = "index"
    rule = "/"
    template_name = "index.html"

    def get(self):
        context = self.get_context()
        return render_template(self.template_name, **context)


class SearchView(ZubbiMethodView):

    endpoint = "search"
    rule = "/search"
    template_name = "search.html"

    def get(self):
        query = request.args.get("query")
        advanced = request.args.get("advanced")
        if query is None:
            context = {
                "result": None,
                "advanced": advanced,
                "default_search_fields": DEFAULT_SEARCH_FIELDS,
                "searchable_block_types": SEARCHABLE_BLOCK_TYPES,
                "searchable_fields": SEARCHABLE_FIELDS,
            }
            context = {**self.get_context(), **context}
            return render_template(self.template_name, **context)

        exact = request.args.get("exact")
        block_filter = request.args.getlist("block_filter")
        fields = request.args.getlist("fields")

        try:
            if len(block_filter) == 1:
                block_class = class_from_block_type(block_filter[0].lower())
            else:
                # Since we only have two block types
                # the filter doesn't make sense in this case
                block_class = None
            filter_from = int(request.args.get("from", 0))
            filter_size = min(
                int(request.args.get("size", current_app.config["SEARCH_BATCH_SIZE"])),
                current_app.config["SEARCH_BATCH_LIMIT"],
            )
            if fields:
                field_set = set(fields)
                # Validate fields
                if not field_set.issubset(SEARCHABLE_FIELDS):
                    abort(400, "The given field is not searchable")

            else:
                field_set = set(DEFAULT_SEARCH_FIELDS)

            # Expand 'name' field to match jobs and roles
            if "name" in field_set:
                field_set.remove("name")
                field_set.update(["job_name", "role_name"])

        except ValueError:
            abort(400)

        filter_to = filter_size + filter_from

        # TODO: This could later be extended with:
        # extra_filter = [Q('term', tenants='<tenant>') | Q('term', private=False)]
        # if we have the tenant information via an Apache Mellon header.
        extra_filter = Q("term", private=False)
        search = BlockSearch(block_class=block_class).search_query(
            query, field_set, exact, extra_filter
        )
        result = search[filter_from:filter_to].execute()

        if len(result) == 1 and filter_from == 0:
            block = result[0]
            return redirect(
                url_for(
                    "zubbi.details",
                    repo=block.repo,
                    block_type=block_type(block),
                    name=block.name,
                ),
                code=303,
            )

        current_page = filter_from // filter_size
        # The last results fit on the second last page. E.g. If we have 9/18/... results
        last_page = max(math.ceil(result.hits.total.value / filter_size) - 1, 0)
        pagination = calculate_pagination(current_page, last_page)

        context = {
            "result": result,
            "query": query,
            "exact": exact,
            "fields": fields,
            "block_filter": block_filter,
            "filter_from": filter_from,
            "pagination": pagination,
            "batch_size": filter_size,
            "advanced": advanced,
            "default_search_fields": DEFAULT_SEARCH_FIELDS,
            "searchable_block_types": SEARCHABLE_BLOCK_TYPES,
            "searchable_fields": SEARCHABLE_FIELDS,
        }
        context = {**self.get_context(), **context}
        return render_template(self.template_name, **context)


class DetailView(ZubbiMethodView):

    endpoint = "details"
    rule = "/detail/<path:repo>/<block_type>/<name>"
    template_name = "details.html"

    def get(self, repo, block_type, name):
        try:
            BlockClass = class_from_block_type(block_type)
        except ValueError:
            abort(400, "Unknown block type '{}'".format(block_type))

        extra_filter = Q("term", private=False)
        search = BlockSearch(block_class=BlockClass).detail_query(
            name, repo, extra_filter
        )
        result = search.execute()

        if not result:
            abort(404, "No {} found with the name '{}'".format(block_type, name))

        context = self.get_context(block_type=block_type, block=result[0])
        return render_template(self.template_name, **context)


class HowToView(ZubbiMethodView):

    endpoint = "how-to"
    rule = "/how-to"
    template_name = "how-to.html"

    def get(self):
        context = self.get_context()
        return render_template(self.template_name, **context)


class AutoCompleteView(ZubbiMethodView):

    endpoint = "auto-complete"
    rule = "/api/search/autocomplete"
    template_name = None

    def get(self):
        term = request.args.get("term")

        if not term:
            json_abort(404)

        # TODO: This could later be extended to filter also for tenants
        # contexts = {
        #     "tenants": ["<tenant>"],
        #     "private": [False]
        # }
        # if we have the tenant information via an Apache Mellon header.
        contexts = {"private": [False]}
        search = BlockSearch().suggest_query(term, size=10, contexts=contexts)
        result = search.execute()

        json_response = set()

        for suggester in result.suggest.suggester:
            for option in suggester.options:
                # NOTE (fschmidt): If we need the result as block class (AnsibleRole,
                # ZuulJob), we could activate the following line
                # block = search._get_result(option.to_dict())
                # json_response.append(block.name)
                json_response.add(option.text)

        return jsonify(list(json_response))


class WebhookView(ZubbiMethodView):

    endpoint = "webhook"
    rule = "/api/webhook"
    template_name = None

    def post(self):
        # Get the payload in the expected format (json)
        # This should also catch payloads which are not json
        payload = request.get_json()
        if not payload:
            json_abort(400, "Payload is missing or not a valid JSON")

        # Check if we received a webhook from GitHub
        if request.headers.get("x-github-delivery") is None:
            json_abort(400, "X-GitHub-Delivery header missing.")

        # Verify that the webhook was sent from our own GitHub app
        # NOTE (fschmidt): We need the raw payload to make the verification work
        self.verify_signature(request.get_data(), request.headers)

        event = self.check_event(request.headers)

        if event is not None:
            get_zmq_socket().send_multipart(
                (event.encode("utf-8"), json.dumps(payload).encode("utf-8"))
            )

        return jsonify({"event_processed": bool(event)})

    def verify_signature(self, payload, headers):
        """Verify that the payload was sent from our GitHub instance."""
        github_signature = headers.get("x-hub-signature")
        if not github_signature:
            json_abort(401, "X-Hub-Signature header missing.")

        gh_webhook_secret = current_app.config["GITHUB_WEBHOOK_SECRET"]
        signature = "sha1={}".format(
            hmac.new(
                gh_webhook_secret.encode("utf-8"), payload, hashlib.sha1
            ).hexdigest()
        )

        if not hmac.compare_digest(signature, github_signature):
            json_abort(401, "Request signature does not match calculated signature.")

    def check_event(self, headers):
        # For now, we are only interested in the following events:
        # - installation {created, deleted}
        # - installation_repositories {added, removed}
        # - push
        event = headers.get("x-github-event")

        if event not in WEBHOOK_EVENTS:
            return None

        return event


class LmzifyView(IndexView):

    endpoint = "lmzify"
    rule = "/lmzify"
    template_name = "lmzify.html"

    def get(self):
        term = request.args.get("term")
        context = self.get_context(term=term)
        return render_template(self.template_name, **context)
