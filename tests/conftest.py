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

import json
import os
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from elasticsearch_dsl.connections import connections

import zubbi
from zubbi.scraper.repos import Repository
from zubbi.utils import urljoin


FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testdata")


def raw_file(filename="repo_files/zuul.d/jobs.yaml"):
    with open(os.path.join(FIXTURE_DIR, filename)) as raw_file:
        content = raw_file.read()
    return content


class DummyRepo(Repository):
    def __init__(self, name):
        self._name = name

    def file_contents(self, file_path):
        pass

    def directory_contents(self, directory_path):
        pass

    def last_changed(self, path):
        pass

    def url_for_file(self, file_path, highlight_start=None, highlight_end=None):
        return "https://github/{}".format(file_path)

    def url_for_directory(self, directory_path):
        return urljoin(self.url, "tree/master", directory_path)

    def blame(self, path):
        pass

    @property
    def url(self):
        return "https://github/{}".format(self._name)

    @property
    def private(self):
        return False

    @property
    def name(self):
        return self._name


@pytest.fixture(scope="function")
def repo_data():
    # TODO (fschmidt): Align this with the MockGitHubRepository in test_integration.py
    # Currently, we always have to adapt both data sets as one is used for the scraper
    # and the other one is used for the parser.
    repo = DummyRepo("my/project")

    tenants = {"jobs": ["foo"], "roles": ["foo", "bar"]}

    job_files = {
        "zuul.d/jobs.yaml": {
            "content": raw_file("repo_files/zuul.d/jobs.yaml"),
            "blame": [],
        },
        "zuul.d/no-jobs.yaml": {
            "content": raw_file("repo_files/zuul.d/no-jobs.yaml"),
            "blame": [],
        },
        "zuul.d/jobs-parse-error.yaml": {
            "content": raw_file("repo_files/zuul.d/jobs-parse-error.yaml"),
            "blame": [],
        },
    }

    role_files = {
        "foo": {
            "last_changed": "2018-09-17 15:15:15",
            "readme_file": {
                "path": "roles/foo/README.rst",
                "content": raw_file("repo_files/roles/foo/README.rst"),
            },
            "changelog_file": None,
        },
        "bar": {
            "last_changed": "2018-09-17 15:15:15",
            "readme_file": {
                "path": "roles/bar/README.rst",
                "content": raw_file("repo_files/roles/bar/README.rst"),
            },
            "changelog_file": None,
        },
    }

    return repo, tenants, job_files, role_files


@pytest.fixture(scope="function")
def github_response_installations():
    response = [
        {
            "id": 94,
            "account": {"login": "admin", "id": 13},
            "integration_id": 15,
            "app_id": 15,
            "target_id": 13,
            "target_type": "Organization",
            "permissions": {"contents": "read", "metadata": "read"},
            "events": [],
            "created_at": "2018-06-21T05:53:40Z",
            "updated_at": "2018-06-21T05:53:40Z",
        }
    ]
    return response


@pytest.fixture(scope="function")
def github_response_repositories():
    response = {
        "total_count": 2,
        "repository_selection": "all",
        "repositories": [
            {
                "id": 186,
                "name": "foobar_repo",
                "full_name": "orga/foo_repo",
                "owner": {
                    "login": "orga",
                    "id": 13,
                    "type": "Organization",
                    "site_admin": False,
                },
                "private": True,
                "description": "foo repo in the orga organization",
                "default_branch": "master",
                "permissions": {"admin": False, "push": False, "pull": False},
            },
            {
                "id": 37,
                "name": "cilib",
                "full_name": "orga/bar_repo",
                "owner": {
                    "login": "orga",
                    "id": 13,
                    "type": "Organization",
                    "site_admin": False,
                },
                "private": False,
                "description": "The bar repo in the orga organization",
                "default_branch": "master",
                "permissions": {"admin": False, "push": False, "pull": False},
            },
        ],
    }

    return response


@pytest.fixture(scope="function")
def github_response_access_token():
    # Mock a future expiry date which will always be valid when calling this
    # function
    expires_future = datetime.now(timezone.utc)
    expires_future += timedelta(minutes=10)
    response = {
        "token": "THIS_IS_NOT_A_TOKEN",
        "expires_at": datetime.strftime(expires_future, "%Y-%m-%dT%H:%M:%SZ"),
    }
    return response


@pytest.fixture(scope="function")
def mock_github_api_endpoints(
    requests_mock,
    github_response_installations,
    github_response_repositories,
    github_response_access_token,
):
    def _github_api(github_url):
        github_api_url = urljoin(github_url, "api/v3")

        # Mock necessary GitHub API endpoints
        requests_mock.get(
            "{}/app/installations".format(github_api_url),
            json=github_response_installations,
        )
        requests_mock.get(
            "{}/installation/repositories?per_page=100".format(github_api_url),
            json=github_response_repositories,
        )
        requests_mock.post(
            "{}/app/installations/94/access_tokens".format(github_api_url),
            json=github_response_access_token,
        )

    return _github_api


@pytest.fixture(scope="function")
def readme_python_code():
    return raw_file("readmes/python-code.rst")


@pytest.fixture(scope="function")
def readme_yaml_code():
    return raw_file("readmes/yaml-code.rst")


@pytest.fixture(scope="function")
def readme_supported_os():
    return raw_file("readmes/supported-os.rst")


@pytest.fixture(scope="function")
def readme_reusable():
    return raw_file("readmes/reusable.rst")


@pytest.fixture(scope="function")
def payload_webhook_installation_created():
    content = raw_file("payloads/github-webhook-installation-created.json")
    return json.loads(content)


@pytest.fixture(scope="function")
def payload_webhook_installation_deleted():
    content = raw_file("payloads/github-webhook-installation-deleted.json")
    return json.loads(content)


@pytest.fixture(scope="function")
def payload_webhook_push():
    content = raw_file("payloads/github-webhook-push.json")
    return json.loads(content)


@pytest.fixture(scope="function")
def flask_client(monkeypatch):
    # Mock elasticsearch connection method which is called when the app is created
    monkeypatch.setattr(zubbi.models, "init_elasticsearch_con", mock.Mock())

    config = {
        "ES_HOST": "localhost",
        "GITHUB_WEBHOOK_SECRET": "some_secret",
        "ZMQ_PUB_SOCKET_ADDRESS": "tcp://*:5555",
        "ZMP_SUB_SOCKET_ADDRESS": "tcp://localhost:5555",
        "ZMQ_SUB_TIMEOUT": 10000,
    }

    app = zubbi.create_app(config=config)
    app.config["TESTING"] = True
    client = app.test_client()

    yield client


@pytest.fixture(scope="function")
def es_client():
    # NOTE (fschmidt): I took a look on how elasticsearch-dsl does the mocking:
    # https://github.com/elastic/elasticsearch-dsl-py/blob/master/test_elasticsearch_dsl/conftest.py
    client = mock.Mock()
    client.search.return_value = {}
    connections.add_connection("default", client)
    yield client
    connections._conn = {}
    connections._kwargs = {}
