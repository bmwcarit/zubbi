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

import contextlib
from pathlib import Path

import pytest
from git import Repo


@pytest.fixture(scope="function")
def mock_git_repo():
    # NOTE (felix): I found that this is better put into a fixture, but I wanted
    # to have the workspace, repo_name and url configurable.
    @contextlib.contextmanager
    def _repo(workspace, repo_name, url):
        repo_workspace = Path(workspace) / repo_name
        mocked_repo = Repo.init(repo_workspace)
        mocked_repo.create_remote("origin", url)

        # Create a readme file and commit it to master
        readme = repo_workspace / "README"
        readme.write_text("Repository: {}".format(repo_name))
        mocked_repo.index.add([str(readme)])
        mocked_repo.index.commit("Initial commit")

        yield mocked_repo

        # TODO (felix): Usually we should do a cleanup here, but as this function is
        # currently only called with a tmpdir, we can do that later on.

    return _repo
