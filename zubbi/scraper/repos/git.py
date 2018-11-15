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

import logging
from pathlib import Path

from git import Repo

from zubbi.scraper.repos import Repository


LOGGER = logging.getLogger(__name__)


# TODO Currently, there is no way to specify a different default branch for a
# "generic" git repository.
# If Gerrit (which will use this implementation) has some similar concept of
# default branches, we have to find a way to implement this.
DEFAULT_BRANCH = "master"


class GitRepository(Repository):
    def __init__(self, repo_name, workspace_dir, remote_url):
        self.repo_name = repo_name
        self.workspace_dir = Path(workspace_dir)
        self.remote_url = remote_url
        self._repo = self._get_repo_object()

    def _get_repo_object(self):
        # Clone the repository if it does not exist, otherwise just fetch it
        # and reset the HEAD.
        repo_src_path = self.workspace_dir / self.repo_name
        if repo_src_path.exists():
            repo = Repo(repo_src_path)
        #    # TODO fetch and reset HEAD
        else:
            repo = Repo.clone_from(self.remote_url, repo_src_path, bare=True, depth=1)
        print(repo)

        return repo

    def check_out_file(self, file_path):
        LOGGER.warning("Checking out '%s'", file_path)
        content = self._repo.git.show("{}:{}".format(DEFAULT_BRANCH, file_path))
        return content

    def list_directory(self, directory_path):
        LOGGER.warning("Listing directory '%s'", directory_path)
        command = ['git', 'ls-tree', '--name-only', DEFAULT_BRANCH]
        # git ls-tree uses the root of the repository automatically, if no path is provided
        # If we provide '/' instead, it will fail.
        if directory_path != '/':
            # We must ensure that the path ends with a slash if we want to get
            # the directory contents
            if not directory_path.endswith('/'):
                directory_path = "{}/".format(directory_path)
            command.append(directory_path)

        files = self._repo.git.execute(command).split()
        print(files)

        # To be compatible with the current GitHub implementation, the resulting
        # dictionary must provide the filename as key and a Contents-like object
        # as value.
        return {Path(f).name: FileContent(f) for f in files}

    def last_changed(self, path):
        pass

    def blame(self, path):
        pass

    @property
    def url(self):
        return self._repo.html_url

    @property
    def private(self):
        return self._repo.private

    @property
    def name(self):
        return self.repo_name


class FileContent:

    def __init__(self, path):
        self.path = path


