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

from datetime import datetime

from zubbi.scraper.connections.github import GitHubConnection


GITHUB_URL = "https://github.example.com"

GITHUB_CON_CONFIG = {
    "app_id": 1,
    "app_key": "tests/testdata/app_key_file",
    "url": GITHUB_URL,
}


def test_get_app_auth_headers():
    # Initialize GitHubConnection
    gh_con = GitHubConnection(**GITHUB_CON_CONFIG)
    gh_con._authenticate()

    result = gh_con._get_app_auth_headers()

    assert result["Accept"] == "application/vnd.github.machine-man-preview+json"
    assert result["Authorization"].startswith("Bearer ")


def test_get_installation_key(mock_github_api_endpoints):

    mock_github_api_endpoints(GITHUB_URL)
    # Initialize GitHubConnection
    gh_con = GitHubConnection(**GITHUB_CON_CONFIG)
    gh_con._authenticate()

    # Calling prime_install_map() includes get_installation_key()
    gh_con._prime_install_map()
    token_from_cache, expires_at = gh_con.installation_token_cache[94]

    # Call get_installation_key() for a specific project (should read from
    # the cache)
    token_for_project = gh_con._get_installation_key(project="orga/foo_repo")

    expected_installation_map = {
        "orga/foo_repo": {"default_branch": "master", "installation_id": 94},
        "orga/bar_repo": {"default_branch": "master", "installation_id": 94},
    }

    assert gh_con.installation_map == expected_installation_map
    assert token_from_cache == "THIS_IS_NOT_A_TOKEN"
    assert token_for_project == "THIS_IS_NOT_A_TOKEN"
    assert isinstance(expires_at, datetime)
