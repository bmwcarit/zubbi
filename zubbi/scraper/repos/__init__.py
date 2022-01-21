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

import abc


class Repository(abc.ABC):
    @abc.abstractmethod
    def file_contents(self, file_path):
        """Check out a single file of this repo."""

    @abc.abstractmethod
    def directory_contents(self, directory_path):
        """List the content of a single directory of this repo."""

    @abc.abstractmethod
    def last_changed(self, path):
        """Get the timestamp of the last commit touching this path."""

    @abc.abstractmethod
    def blame(self, path):
        """Get the blame info for this path."""

    @abc.abstractmethod
    def url(self):
        """Get the URL to this repository."""

    @abc.abstractmethod
    def url_for_file(self, file_path, highlight_start=None, highlight_end=None):
        """Get the URL to the file path."""

    @abc.abstractmethod
    def url_for_directory(self, directory_path):
        """Get the URL for the given directory path."""

    @abc.abstractmethod
    def private(self):
        """Property indicating if the repository is private."""

    @abc.abstractmethod
    def name(self):
        """Property for the name of the repository."""

    def __str__(self):
        return self.name
