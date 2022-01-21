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

import github3
import requests

from zubbi.scraper.exceptions import CheckoutError
from zubbi.scraper.repos import Repository
from zubbi.utils import urljoin


LOGGER = logging.getLogger(__name__)

GRAPHQL_BLAME_QUERY = """
query ($owner: String!, $repo: String!, $path: String!) {
  repository(owner: $owner, name: $repo) {
    defaultBranchRef {
      target {
        ... on Commit {
          blame(path: $path) {
            ranges {
              startingLine
              endingLine
              commit {
                committer {
                  date
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


class GitHubRepository(Repository):
    def __init__(self, repo_name, gh_con):
        self.repo_name = repo_name
        self.gh_con = gh_con
        self._repo = self._get_repo_object()

    def file_contents(self, file_path):
        try:
            LOGGER.debug("Getting file content for '%s'", file_path)
            remote_file_content = self._repo.file_contents(file_path)
            if remote_file_content.size == 0:
                raise CheckoutError(file_path, "File is empty.")
            return remote_file_content.decoded.decode("utf-8")
        except github3.exceptions.NotFoundError:
            raise CheckoutError(file_path, "File not found.")
        except github3.exceptions.UnprocessableResponseBody:
            # This can happen if we try to access a path as file via the
            # GitHub API.
            raise CheckoutError(file_path, "Path is not a file.")

    def directory_contents(self, directory_path):
        try:
            LOGGER.debug("Listing contents of '%s' directory", directory_path)
            remote_directory = self._repo.directory_contents(
                directory_path, return_as=dict
            )
            return remote_directory
        except github3.exceptions.NotFoundError:
            raise CheckoutError(directory_path, "Directory not found.")
        except github3.exceptions.UnprocessableResponseBody:
            raise CheckoutError(directory_path, "Path is not a directory")

    def last_changed(self, path):
        LOGGER.debug("Getting last changes for '%s'", path)
        # We are only interested in the first (newest) commit
        commits = self._repo.commits(path=path, per_page=1)
        commit = next(commits)
        # Get the full commit object
        git_commit = self._repo.git_commit(sha=commit.sha)
        last_changed = git_commit.committer["date"]
        return last_changed

    def blame(self, path):
        LOGGER.debug("Getting blame info for '%s'", path)
        # TODO (fschmidt): When blame is available in GitHub's V4 API, we should
        # switch to this. Until then, we could use the GraphQL to retrieve the
        # necessary information. I'd like to think that the response from GitHub
        # will look the same, so we need to do the parsing and mapping of the
        # response anyway.
        owner, repo = self.repo_name.split("/", 1)

        variables = {"owner": owner, "repo": repo, "path": path}

        token = self.gh_con._get_installation_key(self.repo_name)
        headers = {"Authorization": "bearer {}".format(token)}
        response = requests.post(
            self.gh_con.graphql_url,
            json={"query": GRAPHQL_BLAME_QUERY, "variables": variables},
            headers=headers,
        )

        if response.status_code != 200:
            return []

        blame_json = response.json()

        # Catch error from GraphQL API
        errors = blame_json.get("errors")
        if errors:
            LOGGER.warning(
                "Could not get blame info for %s in '%s'", path, self.repo_name
            )
            for error in errors:
                LOGGER.warning(error["message"])
            return []

        # Flatten the result
        flat_blame = []
        try:
            for blame in blame_json["data"]["repository"]["defaultBranchRef"]["target"][
                "blame"
            ]["ranges"]:
                flat_blame.append(
                    {
                        "start": blame["startingLine"],
                        "end": blame["endingLine"],
                        "date": blame["commit"]["committer"]["date"],
                    }
                )
        except KeyError:
            LOGGER.exception("Unable to retrieve blame info for file %s", path)
        return flat_blame

    def _get_repo_object(self):
        try:
            owner, repo_name = self.repo_name.split("/")
        except ValueError:
            LOGGER.error("Invalid repo name '%s'", self.repo_name)
            return
        gh_client = self.gh_con.create_github_client(self.repo_name)
        if gh_client is None:
            return
        repo = gh_client.repository(owner=owner, repository=repo_name)
        return repo

    def url_for_file(self, file_path, highlight_start=None, highlight_end=None):
        file_url = self._repo.file_contents(file_path).html_url

        if highlight_start is not None:
            file_url = "{}#L{}".format(file_url, highlight_start)

            if highlight_end is not None:
                file_url = "{}-L{}".format(file_url, highlight_end)

        return file_url

    def url_for_directory(self, directory_path):
        return urljoin(self.url, "tree/master", directory_path)

    @property
    def url(self):
        return self._repo.html_url

    @property
    def private(self):
        return self._repo.private

    @property
    def name(self):
        return self.repo_name
