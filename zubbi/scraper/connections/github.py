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

import github3
import jwt
import requests

from zubbi.utils import urljoin


PREVIEW_JSON_ACCEPT = "application/vnd.github.machine-man-preview+json"

LOGGER = logging.getLogger(__name__)


class GitHubConnection:
    def __init__(self, url, app_id, app_key):
        self.base_url = url
        self.api_url = urljoin(url, "api/v3")
        self.graphql_url = urljoin(url, "api/graphql")

        self._app_id = app_id
        self._app_key = app_key

        self.installation_map = {}
        self.installation_token_cache = {}

    def init(self):
        LOGGER.info("Initializing GitHub connection to %s", self.base_url)
        self.authenticate()

    def authenticate(self):
        LOGGER.debug("Authenticating against GitHub")
        try:
            with open(self._app_key, "r") as f:
                app_key = f.read()
        except IOError:
            LOGGER.error("Failed to open app key file: %s", self._app_key)

        if not self._app_id and app_key:
            LOGGER.error(
                "You must provide an app_id and an app_key to use "
                "installation based authentication"
            )
            return

        self.app_id = self._app_id
        self.app_key = app_key

    def _get_app_auth_headers(self):
        """Set the correct auth headers to authenticate against GitHub."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=5)

        data = {"iat": now, "exp": expiry, "iss": self.app_id}
        app_token = jwt.encode(data, self.app_key, algorithm="RS256")

        headers = {
            "Accept": PREVIEW_JSON_ACCEPT,
            "Authorization": "Bearer {}".format(app_token),
        }

        return headers

    def _get_installation_key(self, project):
        """Get the auth token for a project or installation id."""

        # TODO (felix): Look up the installation for the given project.
        # After that check the installation_token_cache for a token for
        # this installation. If none could be found (or the token is
        # expired), request a new one and store it in the cache.
        # TODO (felix): We should change the installation map to
        # org -> installation_id
        # so we don't have to ask the github API for each installation.
        # TODO (felix): What if the installation changed (e.g. the app
        # was reinstalled in a repo/org)?
        # -> This should be handled by the webhook event handlers. But
        # we should implement a fallback that re-requests the
        # installation_id for a project in case we can't request a
        # token or can't access the repo at all (although we expect to
        # do so).

        owner, _ = project.split("/", 1)
        installation_id = self.installation_map.get(owner, {}).get("id")

        if not installation_id:
            # Request the installation id for this orga
            installation_id = self._get_installation_for_owner(owner)

        if not installation_id:
            # TODO (felix): If we still couldn't get the installation id,
            # we most probably don't have access anymore.
            LOGGER.debug("No installation ID available for project %s", project)
            # TODO (felix): Better return None?
            return ""

        # Look up the token from cache
        now = datetime.now(timezone.utc)
        token, expiry = self.installation_token_cache.get(installation_id, (None, None))

        # Request new token if the available one is expired or could not be found
        if (not expiry) or (not token) or (now >= expiry):
            LOGGER.debug("Requesting new token for installation %s", installation_id)
            headers = self._get_app_auth_headers()
            url = "{}/app/installations/{}/access_tokens".format(
                self.api_url, installation_id
            )

            response = requests.post(url, headers=headers)
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

    def _get_installation_for_owner(self, owner):
        # TODO (felix): Fetch the installation id for the given owner,
        # store it in the installation_map (together with the meta data)
        # we got from github (e.g. projects + default branch -> necessary
        # for scraping) and return the installation_id.

        # TODO (felix): Does this also work for users? Usually an owner
        # can be one of both, user or orga.
        url = f"{self.api_url}/orgs/{owner}/installation"
        headers = self._get_app_auth_headers()
        LOGGER.debug("Fetching installation for owner '%s'", owner)

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()

        LOGGER.debug(data)

        installation_id = data["id"]

        # Store the installation id, so we don't have to retrieve it
        # again (unless it changed).
        self.installation_map[owner] = {"id": installation_id}

        # TODO (felix): We should keep track on the repository data somehow
        # to validate the default branch for the push events.

        return installation_id

    def _prime_install_map(self):
        """Fetch all installations and look up the ID for each."""
        url = "{}/app/installations".format(self.api_url)
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

            url = "{}/installation/repositories?per_page=100".format(self.api_url)
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

    def create_github_client(self, project):
        """Create a github3 client per repo/installation."""
        token = self._get_installation_key(project=project)
        if not token:
            LOGGER.warning(
                "Could not find an authentication token for '%s'. Do you "
                "have access to this repository?",
                project,
            )
            return
        gh = github3.GitHubEnterprise(self.base_url)
        gh.login(token=token)
        return gh

    @property
    def repos(self):
        return self.installation_map.keys()

    @property
    def provider(self):
        return "github"

    def get_repos_for_installation(self, install_id):
        return [
            k
            for k, v in self.installation_map.items()
            if v["installation_id"] == install_id
        ]
