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


class GitConnection:
    def __init__(
        self, url, user=None, password=None, workspace="/tmp/zubbi_working_dir"
    ):
        self.git_host_url = url

        # TODO Support password via envvar (like in zapfel)
        self.user = user
        self.password = password

        # TODO (felix): Not sure if the connection is the right scope for this variable,
        # but it's the simplest way to configure it - and one could argue, that the
        # workspace directory is depending on the connection entry in the settings file
        # (different connection -> different workspace)
        self.workspace_dir = workspace

        # TODO If we want to support ssh and https, we should add a protocol parameter

    def init(self):
        LOGGER.info("Initializing Git connection to %s", self.git_host_url)
        # Currently, we don't need to do anything

    def get_remote_url(self, repository_name):
        # TODO (felix): Find a better way to rebuild the url with auth values
        # TODO (felix): Currently, this method requires the git_host_url to
        # provide a schema (e.g. https://)
        scheme, _, url = self.git_host_url.partition("://")

        if self.user and self.password:
            auth_part = "{}:{}@".format(self.user, self.password)
        elif self.user:
            auth_part = "{}@".format(self.user)
        else:
            auth_part = ""

        auth_base_url = "{}://{}{}".format(scheme, auth_part, url)
        remote_url = urljoin(auth_base_url, repository_name)
        return remote_url

    @property
    def provider(self):
        return "git"
