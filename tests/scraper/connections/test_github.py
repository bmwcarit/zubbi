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

import requests_mock

from zubbi.scraper.connections.github import GitHubConnection


GITHUB_URL = "https://github.example.com"
GITHUB_API_URL = "{}/api/v3".format(GITHUB_URL)

GITHUB_CON_CONFIG = {
    "GITHUB_APP_ID": 1,
    "GITHUB_APP_KEY": "tests/testdata/app_key_file",
    "GITHUB_URL": GITHUB_URL,
}


def test_get_app_auth_headers():
    # Initialize GitHubConnection
    gh_con = GitHubConnection(GITHUB_CON_CONFIG)
    gh_con._authenticate()

    result = gh_con._get_app_auth_headers()

    assert result["Accept"] == "application/vnd.github.machine-man-preview+json"
    assert result["Authorization"].startswith("Bearer ")


def test_get_installation_key(
    github_response_installations,
    github_response_repositories,
    github_response_access_token,
):

    # Initialize GitHubConnection
    gh_con = GitHubConnection(GITHUB_CON_CONFIG)
    gh_con._authenticate()

    with requests_mock.Mocker() as m:
        # Mock necessary GitHub API endpoints
        m.get(
            "{}/app/installations".format(GITHUB_API_URL),
            json=github_response_installations,
        )
        m.get(
            "{}/installation/repositories?per_page=100".format(GITHUB_API_URL),
            json=github_response_repositories,
        )
        m.post(
            "{}/installations/94/access_tokens".format(GITHUB_API_URL),
            json=github_response_access_token,
        )

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
    assert token_from_cache == "v1.6a01e67ed5a45dff724d99694a325a090ab69419"
    assert token_for_project == "v1.6a01e67ed5a45dff724d99694a325a090ab69419"
    assert isinstance(expires_at, datetime)
