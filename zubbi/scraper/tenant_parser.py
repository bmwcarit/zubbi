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
import os
from collections import defaultdict

import yaml

from zubbi.scraper.exceptions import CheckoutError, ScraperConfigurationError


TENANTS_DIRECTORY = "tenants"

LOGGER = logging.getLogger(__name__)


class TenantParser:
    def __init__(self, sources_file=None, sources_repo=None):
        self.sources = None
        self.repo_map = {}
        self.tenants = []
        # Initial call to load the sources file/repo
        self.reload_sources(sources_file, sources_repo)

    def reload_sources(self, sources_file=None, sources_repo=None):
        if sources_file:
            self.sources = self._load_tenant_sources_from_file(sources_file)
        else:
            self.sources = self._load_tenant_sources_from_repo(sources_repo)

    def update(self, sources_file=None, sources_repo=None):
        self.reload_sources(sources_file, sources_repo)
        self.parse()

    def parse(self):
        # Clear repo_map and tenant list first
        self.repo_map.clear()
        self.tenants.clear()

        for tenant_src in self.sources:
            sources = tenant_src["tenant"]["source"]
            tenant_name = tenant_src["tenant"]["name"]

            # Iterate over all repositories specified in this tenant (per provider)
            for connection_name, source in sources.items():
                # project_type is config- or untrusted-project
                for project_type, projects in source.items():
                    for project in projects:
                        self._update_repo_map(project, connection_name, tenant_name)

            self.tenants.append(tenant_name)

    def _update_repo_map(self, project, connection_name, tenant):
        result = self._extract_project(project)
        if result is None:
            return

        # Extract tuple values from result
        project_name, exclude, extra_config_paths = result

        # Map the current tenant to the current repository
        repo_tenant_entry = self.repo_map.setdefault(
            project_name,
            {"tenants": {"jobs": [], "roles": []}, "connection_name": connection_name},
        )

        # Update repo_tenant mapping
        if "job" not in exclude:
            repo_tenant_entry["tenants"]["jobs"].append(tenant)
        repo_tenant_entry["tenants"]["roles"].append(tenant)

        if extra_config_paths:
            repo_tenant_extra_config_paths = repo_tenant_entry["tenants"].setdefault(
                "extra_config_paths", defaultdict(lambda: [])
            )
            for extra_config_path in extra_config_paths:
                repo_tenant_extra_config_paths[extra_config_path].append(tenant)

    def _extract_project(self, project):
        # This covers the default case where a project is a simple string
        project_name = project
        exclude = []
        extra_config_paths = []
        # If a project is a dictionary, we have to look up and evaluate
        # certain attributes:
        if type(project) is dict:
            # Get the first key of the dict containing the project name.
            # NOTE: The dict should only contain a single key since each
            # project is a dict entry in a list.
            project_name = list(project.keys())[0]

            if "projects" in project:
                # TODO (felix): This is kind of a "reverse" structure,
                # which is usually used to include/exclude the same
                # configuration items for a lot of projects.
                # This use case is currently not covered in Zubbi, but
                # we might want to implement this later on.
                #
                # Examples:
                #
                # # Include nothing from projects foo, bar
                # - include: []
                #   projects:
                #     - foo
                #     - bar
                #
                # # Exclude jobs and semaphores from foo
                # - exclude:
                #     - job
                #     - semaphore
                #   projects:
                #     - foo
                return

            exclude = project[project_name].get("exclude", [])
            # NOTE (swietlicki): directories in extra-config-path section contain
            # trailing slash, while inside the Scraper.iterate_directory() the comparison
            # is done against dir names without trailing slash
            for item in project[project_name].get("extra-config-paths", []):
                extra_config_paths.append(item[:-1] if item.endswith("/") else item)
        return project_name, exclude, extra_config_paths

    def _load_tenant_sources_from_file(self, sources_file):
        LOGGER.info("Parsing tenant sources file '%s'", sources_file)
        with open(sources_file) as f:
            sources = yaml.safe_load(f)
        return sources

    def _load_tenant_sources_from_repo(self, sources_repo):
        LOGGER.info("Collecting tenant sources from repo '%s'", sources_repo)
        sources = []
        try:
            tenants = sources_repo.directory_contents(TENANTS_DIRECTORY)
        except CheckoutError:
            raise ScraperConfigurationError(
                "Cannot load tenant sources. Repo '{}' does not contain a "
                "'tenants' folder".format(sources_repo.repo_name)
            )

        for tenant in tenants.keys():
            try:
                sources_yaml = sources_repo.file_contents(
                    os.path.join("tenants", tenant, "sources.yaml")
                )
                settings_yaml = sources_repo.file_contents(
                    os.path.join("tenants", tenant, "settings.yaml")
                )
                # NOTE (fschmidt): We parse both files and create the same data
                # structure like zuul does for the main.yaml file.
                tenant_sources = {
                    # Load the settings first, as they contain different keys
                    "tenant": yaml.safe_load(settings_yaml)
                }
                # Update the tenant_sources with the sources file and wrap them
                # in a 'source' key
                tenant_sources["tenant"]["source"] = yaml.safe_load(sources_yaml)

                sources.append(tenant_sources)
            except CheckoutError as e:
                # If a single tenant is missing the required file, we just skip it
                LOGGER.warning(
                    "Either 'settings.yaml' or 'sources.yaml' are "
                    "missing or empty in repo '%s': %s",
                    sources_repo.repo_name,
                    e,
                )
        return sources
