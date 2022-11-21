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

from zubbi.scraper.exceptions import CheckoutError
from zubbi.scraper.repos.github import GitHubRepository
from zubbi.scraper.scraper import REPO_ROOT, Scraper
from zubbi.scraper.tenant_parser import TenantParser


MOCKED_JOB_CONTENT = """
- job:
    name: my-cool-new-job
    parent: cool-base-job
    description: |
      This is just a job for testing purposes.
    run: playbooks/non-existing-playbook.yaml
"""

MOCKED_ROLE_DESCRIPTION = """
Role description containing some reStructuredText expressions.

**Role variables**

.. zuul:rolevar:: mandatory_variable

   This variable is mandatory.
"""


class MockContents:

    FILE = "file"
    DIR = "dir"

    def __init__(self, path, type):
        self.path = path
        self.type = type


class MockGitHubRepository(GitHubRepository):

    # TODO (felix): Improve the mocked repository class and allow mocking
    # single repositories for certain test cases. Currently, all test repos
    # are defined in this class definition.
    # TODO (felix): While doing that, we could also simplify the structure of
    # the testdata within the repository to accept paths and build the
    # "directories" underhood for all parts within a certan path.
    # -> So we end up to use one dict key per file within the repo don't need
    # to specify each directory.

    # project/directory_or_filename
    test_data = {
        "orga1/repo1": {
            REPO_ROOT: {
                "zuul.d": MockContents("zuul.d", MockContents.DIR),
                "roles": MockContents("roles", MockContents.DIR),
            },
            "zuul.d": {
                "jobs.yaml": MockContents("zuul.d/jobs.yaml", MockContents.FILE)
            },
            "zuul.d/jobs.yaml": MOCKED_JOB_CONTENT,
            "roles": {"docker-run": MockContents("roles/docker-run", MockContents.DIR)},
            "roles/docker-run": {
                "README.rst": MockContents(
                    "roles/docker-run/README.rst", MockContents.FILE
                )
            },
            "roles/docker-run/README.rst": MOCKED_ROLE_DESCRIPTION,
            "roles/ignored": MockContents("not a valid role", MockContents.FILE),
        },
        "orga1/repo2": {
            REPO_ROOT: {
                "roles": MockContents("roles", MockContents.DIR),
            },
            "roles": {
                "foo": MockContents("roles/foo", MockContents.DIR),
                "bar": MockContents("roles/bar", MockContents.DIR),
                "foobar": MockContents("roles/foobar", MockContents.DIR),
                "empty-dir": MockContents("roles/empty-dir", MockContents.DIR),
            },
            "roles/foo": {
                "README.md": MockContents("roles/foo/README.md", MockContents.FILE)
            },
            "roles/bar": {
                "README.txt": MockContents("roles/bar/README.txt", MockContents.FILE)
            },
            "roles/foobar": {
                "README": MockContents("roles/foobar/README", MockContents.FILE)
            },
            "roles/empty-dir": {
                "README.whatever": MockContents(
                    "roles/empty-dir/README.whatever", MockContents.FILE
                )
            },
            "roles/foo/README.md": "# Just some Markdown",
            "roles/bar/README.txt": "Just some simple text\nwith a line break",
            "roles/foobar/README": "Simple text in a file without extension",
            "roles/empty-dir/REAMDE.whatever": "This file won't be checked out",
        },
        # Empty repositories
        "orga2/repo1": {},
        "orga2/repo3": {},
    }

    def __init__(self, repo_name):
        self.repo_name = repo_name
        self.gh = mock.Mock()
        self._repo = repo_name

    def directory_contents(self, directory_path):
        # Just list different files based on the given repo (which is the project
        # name in this case) and the directory_path
        try:
            return self.test_data[self.repo_name][directory_path]
        except KeyError:
            raise CheckoutError(directory_path, "Directory does not exist in repo.")

    def file_contents(self, file_path):
        # Just return different file contents based on the combination of
        # repo and file_path
        try:
            return self.test_data[self.repo_name][file_path]
        except KeyError:
            raise CheckoutError(file_path, "File does not exist in repo.")

    def last_changed(self, path):
        return "2018-09-17 15:15:15"

    def blame(self, path):
        return []


def test_scrape():
    expected = {
        "orga1/repo1": (
            {
                "zuul.d/jobs.yaml": {
                    "last_changed": "2018-09-17 15:15:15",
                    "content": "\n- job:\n"
                    "    name: my-cool-new-job\n"
                    "    parent: cool-base-job\n"
                    "    description: |\n"
                    "      This is just a job for testing purposes.\n"
                    "    run: playbooks/non-existing-playbook.yaml\n",
                    "blame": [],
                }
            },
            {
                "docker-run": {
                    "last_changed": "2018-09-17 15:15:15",
                    "readme_file": {
                        "path": "roles/docker-run/README.rst",
                        "content": "\nRole description containing some reStructuredText expressions.\n\n"
                        "**Role variables**\n\n"
                        ".. zuul:rolevar:: mandatory_variable\n\n"
                        "   This variable is mandatory.\n",
                    },
                    "changelog_file": None,
                }
            },
        ),
        "orga1/repo2": (
            {},
            {
                "foo": {
                    "last_changed": "2018-09-17 15:15:15",
                    "readme_file": {
                        "path": "roles/foo/README.md",
                        "content": "# Just some Markdown",
                    },
                    "changelog_file": None,
                },
                "bar": {
                    "last_changed": "2018-09-17 15:15:15",
                    "readme_file": {
                        "path": "roles/bar/README.txt",
                        "content": "Just some simple text\nwith a line break",
                    },
                    "changelog_file": None,
                },
                "foobar": {
                    "last_changed": "2018-09-17 15:15:15",
                    "readme_file": {
                        "path": "roles/foobar/README",
                        "content": "Simple text in a file without extension",
                    },
                    "changelog_file": None,
                },
                "empty-dir": {
                    "last_changed": "2018-09-17 15:15:15",
                    "readme_file": None,
                    "changelog_file": None,
                },
            },
        ),
        "orga2/repo1": ({}, {}),
        "orga2/repo3": ({}, {}),
    }

    tenant_parser = TenantParser(sources_file="tests/testdata/test.foo.yaml")
    tenant_parser.parse()

    tenant_list = tenant_parser.tenants
    repo_map = tenant_parser.repo_map

    assert tenant_list[0] == "foo"
    assert len(tenant_list) == 1

    for repo, tenants in repo_map.items():
        gh_repo = MockGitHubRepository(repo)
        job_files, role_files = Scraper(gh_repo).scrape()
        assert (job_files, role_files) == expected[repo]


def test_scrape_not_github():
    tenant_parser = TenantParser(sources_file="tests/testdata/test.bar.yaml")
    tenant_parser.parse()

    expected_repo_map = {
        "repo1": {
            "connection_name": "gerrit",
            "tenants": {"jobs": ["bar"], "roles": ["bar"]},
        },
        "repo2": {
            "connection_name": "gerrit",
            "tenants": {"jobs": ["bar"], "roles": ["bar"]},
        },
        "repo3": {
            "connection_name": "gerrit",
            "tenants": {"jobs": ["bar"], "roles": ["bar"]},
        },
    }

    tenant_list = tenant_parser.tenants
    repo_map = tenant_parser.repo_map

    assert tenant_list[0] == "bar"
    assert len(tenant_list) == 1
    assert repo_map == expected_repo_map
