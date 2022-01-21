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
from git import Repo

from zubbi.scraper.connections.git import GitConnection
from zubbi.scraper.exceptions import CheckoutError
from zubbi.scraper.repos.git import FileContent, GitRepository


@pytest.mark.parametrize(
    "url, repo_name, expected",
    [
        ("http://localhost", "foo/bar", "http://localhost/foo/bar"),
        ("https://localhost/git", "foo.bar", "https://localhost/git/foo.bar"),
    ],
)
def test_get_remote_url(url, repo_name, expected):
    git_con = GitConnection(url)
    remote_url = git_con.get_remote_url(repo_name)
    assert remote_url == expected


def test_get_repo_object_existing_path(mock_git_repo, tmpdir):
    git_url = "https://localhost/git"
    repo_name = "foo"

    with mock_git_repo(tmpdir, repo_name, git_url):
        git_con = GitConnection(git_url, workspace=tmpdir)
        # The __init__() method calls _get_repo_object()
        git_repo = GitRepository(repo_name, git_con)
        assert isinstance(git_repo._repo, Repo)


def test_get_repo_object_failure(tmpdir):
    git_url = "https://localhost/git"
    repo_name = "foo"

    git_con = GitConnection(git_url, workspace=tmpdir)
    git_repo = GitRepository(repo_name, git_con)
    assert git_repo._repo is None


def test_file_contents(mock_git_repo, tmpdir):
    git_url = "https://localhost/git"
    repo_name = "foo"

    with mock_git_repo(tmpdir, repo_name, git_url):
        git_con = GitConnection(git_url, workspace=tmpdir)
        git_repo = GitRepository(repo_name, git_con)

        contents = git_repo.file_contents("README")
        assert contents == "Repository: foo"


def test_non_existing_file_contents(mock_git_repo, tmpdir):
    git_url = "https://localhost/git"
    repo_name = "foo"

    with mock_git_repo(tmpdir, repo_name, git_url):
        git_con = GitConnection(git_url, workspace=tmpdir)
        git_repo = GitRepository(repo_name, git_con)

        with pytest.raises(CheckoutError) as excinfo:
            git_repo.file_contents("non-existing-file")
        assert "Failed to check out 'non-existing-file'" in str(excinfo.value)


def test_directory_contents(mock_git_repo, tmpdir):
    git_url = "https://localhost/git"
    repo_name = "foo"

    with mock_git_repo(tmpdir, repo_name, git_url):
        git_con = GitConnection(git_url, workspace=tmpdir)
        git_repo = GitRepository(repo_name, git_con)

        contents = git_repo.directory_contents("/")
        # The contents dict should contain an entry for the README file
        readme_contents = contents["README"]
        assert isinstance(readme_contents, FileContent)
        assert readme_contents.path == "README"


def test_non_existing_directory_contents(mock_git_repo, tmpdir):
    git_url = "https://localhost/git"
    repo_name = "foo"

    with mock_git_repo(tmpdir, repo_name, git_url):
        git_con = GitConnection(git_url, workspace=tmpdir)
        git_repo = GitRepository(repo_name, git_con)

        with pytest.raises(CheckoutError) as excinfo:
            git_repo.directory_contents("/non-existing-directory")
        assert "Failed to check out '/non-existing-directory/'" in str(excinfo.value)
