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
from unittest import mock

import pytest

import zubbi
from zubbi.scraper.connections.gerrit import GerritConnection
from zubbi.scraper.connections.git import GitConnection
from zubbi.scraper.connections.github import GitHubConnection
from zubbi.scraper.main import init_connections


@pytest.fixture(scope="function")
def patch_es(monkeypatch):
    # Patch the function where it is used, not the original one
    monkeypatch.setattr(zubbi.scraper.main, "init_elasticsearch_con", mock.Mock())


def test_init_gerrit_con(patch_es):
    config = {
        "ES_HOST": "localhost",
        "CONNECTIONS": {
            "gerrit_con": {
                "provider": "gerrit",
                "url": "https://localhost/gerrit",
                "web_url": "https://localhost/gerrit-web",
                "user": "spam",
                "password": "eggs",
            }
        },
    }

    expected_con_data = {
        "git_host_url": "https://localhost/gerrit",
        "user": "spam",
        "password": "eggs",
        "workspace_dir": "/tmp/zubbi_working_dir",
        "base_url": "https://localhost/gerrit",
        "gitweb_url": "https://localhost/gerrit-web/gitweb",
    }

    connections = init_connections(config)
    gerrit_con = connections["gerrit_con"]

    assert isinstance(gerrit_con, GerritConnection)
    assert gerrit_con.__dict__ == expected_con_data


def test_init_github_con(patch_es, mock_github_api_endpoints):

    config = {
        "ES_HOST": "localhost",
        "CONNECTIONS": {
            "github_con": {
                "provider": "github",
                "url": "https://github.example.com",
                "app_id": 3,
                "app_key": os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "../../testdata/app_key_file",
                ),
            }
        },
    }

    expected_con_data = {
        "base_url": "https://github.example.com",
        "api_url": "https://github.example.com/api/v3",
        "graphql_url": "https://github.example.com/api/graphql",
        "app_id": 3,
    }

    connections = init_connections(config)
    github_con = connections["github_con"]
    assert isinstance(github_con, GitHubConnection)
    # Check that the expected data is a subset of the connection's underlying dict
    for key, val in expected_con_data.items():
        assert val == github_con.__dict__[key]


def test_init_git_con(patch_es):
    config = {
        "ES_HOST": "localhost",
        "CONNECTIONS": {
            "git_con": {
                "provider": "git",
                "url": "https://localhost/git",
                # Optional, if authentication is required
                "user": "foo",
                "password": "bar",
            }
        },
    }

    expected_con_data = {
        "git_host_url": "https://localhost/git",
        "user": "foo",
        "password": "bar",
        "workspace_dir": "/tmp/zubbi_working_dir",
    }

    connections = init_connections(config)
    git_con = connections["git_con"]

    assert isinstance(git_con, GitConnection)
    assert expected_con_data == git_con.__dict__
