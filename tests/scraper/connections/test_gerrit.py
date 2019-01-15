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

from zubbi.scraper.connections.gerrit import CGitUrlBuilder, GitwebUrlBuilder


@pytest.mark.parametrize(
    "gerrit_url, repo_name, file_path, highlight_start, expected",
    [
        (
            "https://gerrit.example.com/",
            "bar",
            "roles/bar/README.md",
            1,
            "https://gerrit.example.com/bar/tree/roles/bar/README.md#n1",
        ),
        (
            "git.example.org/cgit",
            "foo",
            "config.yaml",
            None,
            "git.example.org/cgit/foo/tree/config.yaml",
        ),
    ],
)
def test_url_for_file_cgit(gerrit_url, repo_name, file_path, highlight_start, expected):
    url_builder = CGitUrlBuilder(gerrit_url)
    file_url = url_builder.build_file_url(repo_name, file_path, highlight_start, None)
    assert file_url == expected


@pytest.mark.parametrize(
    "gerrit_url, repo_name, file_path, highlight_start, expected",
    [
        (
            "https://gerrit.example.com/",
            "bar",
            "roles/bar/README.md",
            1,
            "https://gerrit.example.com/?p=bar.git;a=blob;f=roles/bar/README.md#l1",
        ),
        (
            "git.example.org/gitweb",
            "foo",
            "config.yaml",
            None,
            "git.example.org/gitweb?p=foo.git;a=blob;f=config.yaml",
        ),
    ],
)
def test_url_for_file_gitweb(
    gerrit_url, repo_name, file_path, highlight_start, expected
):
    url_builder = GitwebUrlBuilder(gerrit_url)
    file_url = url_builder.build_file_url(repo_name, file_path, highlight_start, None)
    assert file_url == expected
