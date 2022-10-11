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

import pytest


@pytest.mark.parametrize(
    "endpoint, expected",
    [
        ("/", "200 OK"),
        ("/search", "200 OK"),
        ("/how-to", "200 OK"),
        ("/lmzify", "200 OK"),
    ],
)
def test_views_reachable(flask_client, endpoint, expected):
    """Test if all available views in zubbi are reachable."""
    rv = flask_client.get(endpoint)
    assert rv.status == expected


def test_detail_view(flask_client, es_client):

    # Build a simple ES response, containing a minimal role result
    response = {
        "hits": {
            "hits": [
                {
                    "_index": "ansible-roles",
                    "_type": "doc",
                    "_source": {"role_name": "foo", "repo": "repo_name"},
                }
            ]
        }
    }

    es_client.search.return_value = response
    # TODO (fschmidt): Make this work similar to requests.mock
    # where we can mock each request/response inside the context
    rv = flask_client.get("/detail/repo_name/role/foo")
    assert rv.status == "200 OK"
    assert b"<title>Details for role foo - Zubbi</title>" in rv.data


def test_detail_view_unknown_block_type(flask_client):
    rv = flask_client.get("/detail/repo_name/foobar/foo")
    assert rv.status == "400 BAD REQUEST"
    assert b"Unknown block type" in rv.data


def test_auto_complete_view(flask_client, es_client):
    response = {
        "suggest": {"suggester": [{"options": [{"text": "foo"}, {"text": "foobar"}]}]}
    }

    es_client.search.return_value = response
    rv = flask_client.get("/api/search/autocomplete?term=foo")
    # The resulting list is not ordered
    assert set(rv.get_json()) == {"foobar", "foo"}


@pytest.mark.parametrize(
    "params",
    [
        "",  # no parameter at all
        "?term",  # correct parameter, but missing value
        "?foobar=abc",  # wrong parameter
    ],
)
def test_auto_complete_view_error(flask_client, params):
    rv = flask_client.get("/api/search/autocomplete{}".format(params))
    assert rv.status == "404 NOT FOUND"
    assert rv.get_json() == {"error": 404}


def test_webhook_view_get(flask_client):
    # Don't accept get requests
    rv_get = flask_client.get("/api/webhook")
    assert rv_get.status == "405 METHOD NOT ALLOWED"


def test_webhook_view_missing_payload(flask_client):
    rv_post_empty = flask_client.post("/api/webhook", json={})
    assert rv_post_empty.status == "400 BAD REQUEST"
    assert rv_post_empty.get_json() == {
        "error": 400,
        "msg": "Payload is missing or not a valid JSON",
    }


def test_webhook_view_wrong_sha(flask_client):
    # Valid payload, but wrong sha
    rv_post_invalid = flask_client.post(
        "/api/webhook",
        json={"abc": "cde"},
        headers={
            "X-GitHub-Delivery": "foo",
            "X-Hub-Signature": "wrong_sha",
            "x-Github-Event": "installation",
        },
    )
    assert rv_post_invalid.status == "401 UNAUTHORIZED"
    assert rv_post_invalid.get_json() == {
        "error": 401,
        "msg": "Request signature does not match calculated signature.",
    }


def test_webhook_view_correct_sha(flask_client):
    # Valid payload with precalculated sha
    precalculated_signature = "sha1=3e7397e4c518017be42e2a87522ae117edc422c9"

    rv_post_valid = flask_client.post(
        "/api/webhook",
        json={"abc": "cde"},
        headers={
            "X-GitHub-Delivery": "foo",
            "X-Hub-Signature": precalculated_signature,
            "x-Github-Event": "installation",
        },
    )
    assert rv_post_valid.status == "200 OK"
    assert rv_post_valid.get_json() == {"event_processed": True}
