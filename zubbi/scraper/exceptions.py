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


class RepositoryError(Exception):
    """Base class for all repository related errors."""

    pass


class CheckoutError(RepositoryError):
    """Exception if a file could not be checked out."""

    def __init__(self, path, cause, msg=None):
        if msg is None:
            msg = "Failed to check out '{}': {}".format(path, cause)
        super().__init__(msg)


class ScraperConfigurationError(Exception):
    """Exception if the scraper configuration is wrong."""

    pass
