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
from zubbi.utils import urljoin


LOGGER = logging.getLogger(__name__)


class GerritConnection(GitConnection):
    # TODO (felix): Should we ensure that only the user that started zubbi has access rights
    # to this workspace directory?
    def __init__(
        self, url, user, password, workspace="/tmp/zubbi_working_dir", web_url=None
    ):
        super().__init__(url, user, password, workspace)
        self.base_url = url
        self.gitweb_url = urljoin(web_url or url, "gitweb")

        self.user = user
        self.password = password

    def init(self):
        LOGGER.info("Initializing Gerrit connection to %s", self.base_url)
        # Currently we don't need to do anything here

    @property
    def provider(self):
        return "gerrit"
