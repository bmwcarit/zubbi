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

from zubbi.scraper.connections.git import GitConnection


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
