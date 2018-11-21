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

from zubbi.utils import urljoin


LOGGER = logging.getLogger(__name__)


class GerritConnection:
    # TODO (felix): Should we ensure that only the user that started zubbi has access rights
    # to this workspace directory?
    def __init__(
        self, url, user, password, workspace="/tmp/zubbi_working_dir", web_url=None
    ):
        self.base_url = url
        self.gitweb_url = urljoin(web_url or url, "gitweb")

        # TODO (felix): Not sure if the connection is the right scope for this variable,
        # but it's the simplest way to configure it - and one could argue, that the
        # workspace directory is depending on the connection entry in the settings file
        # (different connection -> different workspace)
        self.workspace_dir = workspace

        # TODO Support password via envvar (like in zapfel)
        self.user = user
        self.password = password

        # TODO If we want to support ssh and https, we should add a protocol parameter

    def init(self):
        LOGGER.info("Initializing Gerrit connection to %s", self.base_url)
        # Currently we don't need to do anything here

    def get_remote_url(self, repository_name):
        # TODO (felix) Find a better way to rebuild the url with auth values
        scheme, _, url = self.base_url.partition("://")
        auth_base_url = "{}://{}:{}@{}".format(scheme, self.user, self.password, url)
        remote_url = urljoin(auth_base_url, repository_name)
        return remote_url

    @property
    def provider(self):
        return "gerrit"
