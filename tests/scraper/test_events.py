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

from unittest import mock

import pytest

from zubbi.scraper.connections.github import GitHubConnection
from zubbi.scraper.main import event_installation, event_push, handle_event


@pytest.fixture(scope="function")
def patched_connections():
    # For the webhook part, we have to ensure a connection named "github"
    connections = {
        "github": GitHubConnection(
            app_id=1,
            app_key="tests/testdata/app_key_file",
            url="https://github.example.com",
        )
    }
    return connections


def test_unknown_event(patched_connections):
    # An unknown event shouldn't do anything, neither throw an exception
    handle_event(
        "unknown",
        None,
        patched_connections,
        reusable_repos=[],
        tenant_parser=None,
        repo_cache=None,
    )


@mock.patch("zubbi.scraper.main.scrape_repo_list")
def test_event_installation_created(
    scrape_mock, patched_connections, payload_webhook_installation_created
):
    # NOTE (felix): When testing the event handling, it should be enough to
    # check if the correct methods are called in the correct ways. The
    # functionality of those methods should be tested somewhere else.
    event_installation(
        payload_webhook_installation_created,
        patched_connections,
        reusable_repos=[],
        tenant_parser=None,
        repo_cache=None,
    )

    # Ensure that the scrape method is called with the correct list of repositories
    assert scrape_mock.call_args == mock.call(
        [
            "zubbi-oss/testsub1",
            "zubbi-oss/testsub2",
            "zubbi-oss/testbase1",
            "zubbi-oss/demo",
            "playground/testsub3",
        ],
        patched_connections,
        [],
        None,
        repo_cache=None,
    )


@mock.patch("zubbi.scraper.main.scrape_repo_list")
def test_event_installation_deleted(
    scrape_mock, patched_connections, payload_webhook_installation_deleted
):

    # Ensure that some repositories can be looked up for this installation as they
    # are not part of the payload for a delete event.
    with mock.patch(
        "zubbi.scraper.connections.github.GitHubConnection.get_repos_for_installation",
        return_value=["org/foo", "org/bar"],
    ):
        event_installation(
            payload_webhook_installation_deleted,
            patched_connections,
            reusable_repos=[],
            tenant_parser=None,
            repo_cache=None,
        )

    # Ensure that the scrape method is called with the correct list of repos
    # and the delete_only flag.
    assert scrape_mock.call_args == mock.call(
        ["org/foo", "org/bar"],
        patched_connections,
        [],
        None,
        repo_cache=None,
        delete_only=True,
    )


@mock.patch("zubbi.scraper.main.scrape_repo_list")
def test_event_push(scrape_mock, patched_connections, payload_webhook_push):
    # Ensure that the repository from the payload is part of our GitHub connection
    # and has a valid default branch.
    gh_con = patched_connections.get("github")
    gh_con.installation_map = {"zubbi-oss/testsub1": {"default_branch": "master"}}

    event_push(
        payload_webhook_push,
        patched_connections,
        reusable_repos=[],
        tenant_parser=None,
        repo_cache=None,
    )

    # Ensure that the scrape method is called with the correct list of repositories
    assert scrape_mock.call_args == mock.call(
        ["zubbi-oss/testsub1"], patched_connections, [], None, repo_cache=None
    )


@mock.patch("zubbi.scraper.connections.github.GitHubConnection._prime_install_map")
def test_event_push_missing_repo(
    scrape_reprime, patched_connections, payload_webhook_push
):
    event_push(
        payload_webhook_push,
        patched_connections,
        reusable_repos=[],
        tenant_parser=None,
        repo_cache=None,
    )

    # As we did not add the required repository to our GitHub connection, it should
    # try to re-init the installation map.
    assert scrape_reprime.call_count == 1


@mock.patch("zubbi.scraper.main.scrape_repo_list")
def test_event_push_invalid_branch(
    scrape_mock, patched_connections, payload_webhook_push
):
    # Ensure that the repository from the payload is part of our GitHub connection and has
    # a default branch other than "master".
    gh_con = patched_connections.get("github")
    gh_con.installation_map = {"zubbi-oss/testsub1": {"default_branch": "not-master"}}

    event_push(
        payload_webhook_push,
        patched_connections,
        reusable_repos=[],
        tenant_parser=None,
        repo_cache=None,
    )

    # As the branch from the payload is different from the default branch we defined above,
    # the event shouldn't be handled, and thus the scrape method shouldn't have been called.
    assert not scrape_mock.called
