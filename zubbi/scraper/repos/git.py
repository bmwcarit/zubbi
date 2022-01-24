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
from git.exc import GitCommandError, InvalidGitRepositoryError

from zubbi.scraper.exceptions import CheckoutError
from zubbi.scraper.repos import Repository


LOGGER = logging.getLogger(__name__)

# TODO Currently, there is no way to specify a different default branch for a "generic" git repository.
# If Gerrit (which will use this implementation) has some similar concept of
# default branches, we have to find a way to implement this.
DEFAULT_BRANCH = "master"


class GitRepository(Repository):
    def __init__(self, repo_name, git_con):
        self.repo_name = repo_name
        self.workspace_dir = Path(git_con.workspace_dir)
        # Build the remote url based on the gerrit connection parameters
        self.remote_url = git_con.get_remote_url(repo_name)
        self._repo = self._get_repo_object(retry=True)

    def _get_repo_object(self, retry=False):
        # Clone the repository if it does not exist, otherwise just fetch it
        # and reset the HEAD.
        repo_src_path = self.workspace_dir / self.repo_name
        repo = None
        if repo_src_path.exists():
            try:
                repo = Repo(repo_src_path)
                # TODO fetch and reset HEAD
                # TODO Which remote?
                repo.remotes["origin"].fetch(DEFAULT_BRANCH)
            except GitCommandError as e:
                LOGGER.error("Fetching repo '%s' failed: %s" % (self.repo_name, e))
            except InvalidGitRepositoryError as e:
                LOGGER.error(
                    "Could not use existing repository in '%s': %s" % (repo_src_path, e)
                )
        else:
            try:
                repo = Repo.clone_from(
                    self.remote_url, repo_src_path, bare=True, depth=1
                )
            except GitCommandError as e:
                LOGGER.error("Cloning repo '%s' failed: %s" % (self.repo_name, e))

        if repo is None and retry:
            LOGGER.info("Retrying clone/fetch once")
            return self._get_repo_object()

        return repo

    def file_contents(self, file_path):
        try:
            LOGGER.debug("Checking out '%s'", file_path)
            content = self._repo.git.show("{}:{}".format(DEFAULT_BRANCH, file_path))
            return content
        except GitCommandError as e:
            raise CheckoutError(file_path, e.stderr)

    def directory_contents(self, directory_path):
        LOGGER.debug("Listing contents of '%s' directory", directory_path)
        command = ["git", "ls-tree", "--name-only", DEFAULT_BRANCH]
        # git ls-tree uses the root of the repository automatically, if no path is provided
        # If we provide '/' instead, it will fail.
        if directory_path != "/":
            # We must ensure that the path ends with a slash if we want to get
            # the directory contents
            if not directory_path.endswith("/"):
                directory_path = "{}/".format(directory_path)
            command.append(directory_path)

        try:
            files = self._repo.git.execute(command).split()
            # To be compatible with the current GitHub implementation, the resulting
            # dictionary must provide the filename as key and a Contents-like object
            # as value.
            return {Path(f).name: FileContent(f) for f in files}
        except GitCommandError as e:
            raise CheckoutError(directory_path, e.stderr)

    def last_changed(self, path):
        # TODO Implement...
        pass

    def blame(self, path):
        # TODO Implement...
        pass

    def url_for_file(self, file_path, highlight_start=None, highlight_end=None):
        # NOTE (fschmidt): This does not make sense for plain git repositories.
        # It should be implemented by more concrete provider implementations like
        # GitHub or Gerrit.
        return None

    def url_for_directory(self, directory_path):
        # NOTE (fschmidt): This does not make sense for plain git repositories.
        # It should be implemented by more concrete provider implementations like
        # GitHub or Gerrit.
        return None

    @property
    def url(self):
        # NOTE (fschmidt): This does not make sense for plain git repositories.
        # It should be implemented by more concrete provider implementations like
        # GitHub or Gerrit.
        return None

    @property
    def private(self):
        # NOTE (fschmidt): This does not make sense for plain git repositories.
        # It should be implemented by more concrete provider implementations like
        # GitHub or Gerrit.
        return False

    @property
    def name(self):
        return self.repo_name


class FileContent:
    """Minimalistic class that provides the same API as GitHub's Contents class."""

    def __init__(self, path):
        self.path = path
