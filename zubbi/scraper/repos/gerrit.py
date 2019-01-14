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

from zubbi.scraper.repos.git import GitRepository


class GerritRepository(GitRepository):
    # NOTE (fschmidt): As the Gerrit API does not support everything we need,
    # we let the GitRepository do all the checkouts and directory listings
    # and use the gerrit API only for building the URLs which are shown in zubbi.

    def __init__(self, repo_name, gerrit_con):
        self.gerrit_con = gerrit_con
        # Initialize the plain git repository via the GitRepository base class
        super().__init__(repo_name, gerrit_con)

    def url_for_file(self, file_path, highlight_start=None, highlight_end=None):
        return self.gerrit_con.web_url_builder.build_file_url(
            self.repo_name, file_path, highlight_start, highlight_end
        )

    def url_for_directory(self, directory_path):
        return self.gerrit_con.web_url_builder.build_directory_url(
            self.repo_name, directory_path
        )
