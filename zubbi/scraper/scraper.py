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

from zubbi.scraper.exceptions import CheckoutError


LOGGER = logging.getLogger(__name__)

ZUUL_DIRECTORIES = ["zuul.d", ".zuul.d"]

ZUUL_FILES = ["zuul.yaml", ".zuul.yaml"]

README_FILES = ["README.rst", "README.md", "README.txt", "README"]

CHANGELOG_FILES = ["CHANGELOG.rst", "CHANGELOG.md", "CHANGELOG.txt", "CHANGELOG"]

ROLES_DIRECTORY = "roles"

REPO_ROOT = "/"


class Scraper:
    def __init__(self, repo):
        self.repo = repo

    def scrape(self):
        LOGGER.info("Scraping '%s'", self.repo.name)

        # TODO (felix): Currently we are scraping all files of a single
        # repository before we start parsing them. This might load a lot
        # of files into memory. Could we change the workflow and fetch +
        # parse each file directly. I'm not sure if we do some
        # cross-references between files. I have to check this. At least
        # for roles this shouldn't be a problem, as a single role
        # directory is self-contained.
        job_files = self.scrape_job_files()
        role_files = self.scrape_role_files()

        return job_files, role_files

    def scrape_job_files(self):

        job_files = self.iterate_directory(
            REPO_ROOT,
            whitelist=ZUUL_DIRECTORIES + ZUUL_FILES,
            # NOTE (felix): As we provide this directly to the
            # str.endswith() method, the argument must be a str or a
            # tuple of strings, otherwise the following exception is
            # raised:
            #
            # TypeError: endswith first arg must be str or a tuple of
            # str, not list
            file_extensions=(".yaml"),
        )
        return job_files

    def iterate_directory(
        self, path, file_infos=None, whitelist=None, file_extensions=None
    ):
        if file_extensions is None:
            # By default, we don't want to filter any files, so we use
            # an empty string as default "extension".
            file_extensions = ""

        if file_infos is None:
            file_infos = {}

        remote_files = self.repo.directory_contents(path)

        for file_name, remote_file in remote_files.items():
            # Skip files/directories that do not match the whitelist.
            # NOTE (felix): The whitelist is not forwarded and only
            # evaluated on top level.
            if whitelist and file_name not in whitelist:
                continue

            if remote_file.type == "dir":
                try:
                    self.iterate_directory(
                        remote_file.path, file_infos, file_extensions=file_extensions
                    )
                except CheckoutError as e:
                    LOGGER.exception(
                        "Unable to get check out directory '%s': %s",
                        remote_file.path,
                        e,
                    )
            elif remote_file.type == "file":
                # Skip files that don't match the required extension
                if not file_name.endswith(file_extensions):
                    LOGGER.debug(
                        "Skipping file '%s' as file matchers %s don't apply",
                        file_name,
                        file_extensions,
                    )
                    continue
                file_info = self.get_file_info(remote_file.path)
                if file_info:
                    file_infos[remote_file.path] = file_info
            else:
                # There are other file types like symlink or submodule,
                # but we ignore them for now.
                LOGGER.debug(
                    "Ignoring file type '%s' in path '%s'",
                    remote_file.type,
                    remote_file.path,
                )
        return file_infos

    def get_file_info(self, path):
        file_info = {}
        try:
            file_info = {
                "last_changed": self.repo.last_changed(path),
                "blame": self.repo.blame(path),
                "content": self.repo.file_contents(path),
            }
        except CheckoutError as e:
            LOGGER.debug("Unable to get file info for '%s': %s", path, e)

        return file_info

    def scrape_role_files(self):
        role_files = {}
        # We are only interested in the role name (=> directory name)
        # and the README and CHANGELOG files. Thus, we don't need to
        # iterate recursively over the roles directory as those files
        # should be on the top-level per role.
        try:
            roles = self.repo.directory_contents(ROLES_DIRECTORY)
            for role_name, remote_file in roles.items():
                try:
                    if remote_file.type != "dir":
                        # Ansible requires the role to be defined in a
                        # certain directory structure. Thus, we can
                        # ignore it in case it's not a directory.
                        continue
                    last_changed = self.repo.last_changed(remote_file.path)
                    existing_files = self.repo.directory_contents(remote_file.path)
                    # Skip empty directories or files
                    if not existing_files:
                        continue
                    readme_file = self.find_matching_file(README_FILES, existing_files)
                    changelog_file = self.find_matching_file(
                        CHANGELOG_FILES, existing_files
                    )
                    role_files[role_name] = {
                        "last_changed": last_changed,
                        "readme_file": readme_file,
                        "changelog_file": changelog_file,
                    }
                except CheckoutError as e:
                    LOGGER.exception(e)
        except CheckoutError as e:
            LOGGER.debug(e)

        return role_files

    def find_matching_file(self, file_filter, existing_files):
        for filename, file_content in existing_files.items():
            if filename not in file_filter:
                continue
            try:
                rel_path = file_content.path
                # Return the first matching file
                match = {
                    "path": rel_path,
                    "content": self.repo.file_contents(rel_path),
                }
                return match
            except CheckoutError as e:
                LOGGER.exception(e)
