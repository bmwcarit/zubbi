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

from zubbi.scraper.connections.git import GitConnection
from zubbi.scraper.exceptions import ScraperConfigurationError
from zubbi.utils import urljoin


LOGGER = logging.getLogger(__name__)


class CGitUrlBuilder:
    def __init__(self, web_url):
        self.web_url = web_url

    def build_file_url(self, repo_name, file_path, highlight_start, highlight_end):
        file_url = urljoin(self.web_url, repo_name, "tree", file_path)

        if highlight_start is not None:
            file_url = "{}#n{}".format(file_url, highlight_start)
        # NOTE (felix): highlighting a range is not supported by cgit

        return file_url

    def build_directory_url(self, repo_name, directory_path):
        directory_url = urljoin(self.web_url, repo_name, "tree", directory_path)
        return directory_url


class GitwebUrlBuilder:
    def __init__(self, web_url):
        self.web_url = web_url

    def build_file_url(self, repo_name, file_path, highlight_start, highlight_end):
        file_url = "{}?p={}.git;a=blob;f={}".format(self.web_url, repo_name, file_path)

        if highlight_start is not None:
            file_url = "{}#l{}".format(file_url, highlight_start)
        # NOTE (felix): highlighting a range is not supported by gitweb

        return file_url

    def build_directory_url(self, repo_name, directory_path):
        url = "{}?p={}.git;a=tree;f={}".format(self.web_url, repo_name, directory_path)
        return url


class GerritConnection(GitConnection):

    WEB_URL_BUILDERS = {"cgit": CGitUrlBuilder, "gitweb": GitwebUrlBuilder}

    # TODO (felix): Should we ensure that only the user that started zubbi has access rights
    # to this workspace directory?
    def __init__(
        self,
        url,
        user=None,
        password=None,
        workspace="/tmp/zubbi_working_dir",
        web_type="cgit",
        web_url=None,
    ):
        super().__init__(url, user, password, workspace)
        self.base_url = url
        self.gitweb_type = web_type
        self.gitweb_url = web_url or url
        self.web_url_builder = self.get_web_url_builder(web_type, web_url, url)

    def init(self):
        LOGGER.info("Initializing Gerrit connection to %s", self.base_url)
        # Currently we don't need to do anything here

    @property
    def provider(self):
        return "gerrit"

    def get_web_url_builder(self, web_type, web_url, url):
        web_url = web_url or url
        url_builder_class = self.WEB_URL_BUILDERS.get(web_type)
        if url_builder_class is None:
            raise ScraperConfigurationError(
                "Could not initialize Gerrit connection due to an unsupported web_type '{}'".format(
                    web_type
                )
            )
        return url_builder_class(web_url)
