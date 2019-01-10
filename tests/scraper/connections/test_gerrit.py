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

from zubbi.scraper.connections.gerrit import GerritConnection
from zubbi.scraper.repos.gerrit import GerritRepository


def test_url_for_file(mock_git_repo, tmpdir):
    git_url = "https://gerrit.example.com/"
    repo_name = "bar"

    with mock_git_repo(tmpdir, repo_name, git_url):
        gerrit_con = GerritConnection(git_url, "user", "password", workspace=tmpdir)
        gerrit_repo = GerritRepository(repo_name, gerrit_con)

        file_url = gerrit_repo.url_for_file(
            "README", highlight_start=4, highlight_end=9
        )
        assert (
            file_url == "https://gerrit.example.com/gitweb?p=bar.git;a=blob;f=README#l4"
        )


def test_url_for_directory(mock_git_repo, tmpdir):
    git_url = "https://gerrit.example.com/"
    repo_name = "bar"

    with mock_git_repo(tmpdir, repo_name, git_url):
        gerrit_con = GerritConnection(git_url, "user", "password", workspace=tmpdir)
        gerrit_repo = GerritRepository(repo_name, gerrit_con)

        file_url = gerrit_repo.url_for_directory("roles")
        assert file_url == "https://gerrit.example.com/gitweb?p=bar.git;a=tree;f=roles"
