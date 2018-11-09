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
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import jwt
import requests


PREVIEW_JSON_ACCEPT = "application/vnd.github.machine-man-preview+json"

LOGGER = logging.getLogger(__name__)


class GitHubConnection:
    def __init__(self, config):
        self.config = config

        self.base_url = urljoin(self.config["GITHUB_URL"], "api/v3")
        self.graphql_url = urljoin(self.config["GITHUB_URL"], "api/graphql")

        self.app_id = None
        self.app_key = None

        self.installation_map = {}
        self.installation_token_cache = {}

    def onLoad(self):
        LOGGER.debug("Authenticating against GitHub")
        self._authenticate()
        self._prime_install_map()

    def _authenticate(self):
        app_id = self.config.get("GITHUB_APP_ID")
        app_key_file = self.config.get("GITHUB_APP_KEY")
        try:
            with open(app_key_file, "r") as f:
                app_key = f.read()
        except IOError:
            LOGGER.error("Failed to open app key file: %s", app_key_file)

        if not app_id and app_key:
            LOGGER.error(
                "You must provide an app_id and an app_key to use "
                "installation based authentication"
            )
            return

        self.app_id = app_id
        self.app_key = app_key

    def _get_app_auth_headers(self):
        """Set the correctt auth headers to authenticate against GitHub."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=5)

        data = {"iat": now, "exp": expiry, "iss": self.app_id}
        app_token = jwt.encode(data, self.app_key, algorithm="RS256").decode("utf-8")

        headers = {
            "Accept": PREVIEW_JSON_ACCEPT,
            "Authorization": "Bearer {}".format(app_token),
        }

        return headers

    def _get_installation_key(
        self, project, user_id=None, install_id=None, reprime=False
    ):
        """Get the auth token for a project or installation id."""
        installation_id = install_id
        if project is not None:
            installation_id = self.installation_map.get(project, {}).get(
                "installation_id"
            )

        if not installation_id:
            if reprime:
                # prime installation map and try again without refreshing
                self._prime_install_map()
                return self._get_installation_key(
                    project, user_id=user_id, install_id=install_id, reprime=False
                )
            LOGGER.debug("No installation ID available for project %s", project)
            return ""

        # Look up the token from cache
        now = datetime.now(timezone.utc)
        token, expiry = self.installation_token_cache.get(installation_id, (None, None))

        # Request new token if the available one is expired or could not be found
        if (not expiry) or (not token) or (now >= expiry):
            LOGGER.debug("Requesting new token for installation %s", installation_id)
            headers = self._get_app_auth_headers()
            url = "{}/installations/{}/access_tokens".format(
                self.base_url, installation_id
            )

            json_data = {"user_id": user_id} if user_id else None

            response = requests.post(url, headers=headers, json=json_data)
            response.raise_for_status()

            data = response.json()

            token = data["token"]
            expiry = datetime.strptime(data["expires_at"], "%Y-%m-%dT%H:%M:%SZ")
            # Update time zone of expiration date to make it comparable with now()
            expiry = expiry.replace(tzinfo=timezone.utc)

            # Assume, that the token expires two minutes earlier, to not
            # get lost during the checkout/scraping?
            expiry -= timedelta(minutes=2)

            self.installation_token_cache[installation_id] = (token, expiry)

        return token

    def _prime_install_map(self):
        """Fetch all installations and look up the ID for each."""
        url = "{}/app/installations".format(self.base_url)
        headers = self._get_app_auth_headers()
        LOGGER.debug("Fetching installations for GitHub app")

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()

        for install in data:
            install_id = install.get("id")
            token = self._get_installation_key(project=None, install_id=install_id)
            headers = {
                "Accept": PREVIEW_JSON_ACCEPT,
                "Authorization": "token {}".format(token),
            }

            url = "{}/installation/repositories?per_page=100".format(self.base_url)
            while url:
                LOGGER.debug("Fetching repos for installation %s", install_id)
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                repos = response.json()

                # Store all projects in the installation map
                for repo in repos.get("repositories", []):
                    # TODO (fschmidt): Store the installation's
                    # permissions (could come in handy for later features)
                    project_name = repo["full_name"]
                    self.installation_map[project_name] = {
                        "installation_id": install_id,
                        "default_branch": repo["default_branch"],
                    }

                # Check if we need to do further page calls
                url = response.links.get("next", {}).get("url")

    @property
    def repos(self):
        return self.installation_map.keys()

    def get_repos_for_installation(self, install_id):
        return [
            k
            for k, v in self.installation_map.items()
            if v["installation_id"] == install_id
        ]
