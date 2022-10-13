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

import hashlib
import logging

import yaml
from yaml.composer import Composer
from yaml.constructor import Constructor
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from zubbi.doc import render_file, render_sphinx, SphinxBuildError
from zubbi.models import AnsibleRole, ZuulJob
from zubbi.utils import last_changed_from_blame_range


LOGGER = logging.getLogger(__name__)


class RepoParser:
    def __init__(
        self, repo, tenants, job_files, role_files, scrape_time, is_reusable_repo
    ):
        self.repo = repo
        self.tenants = tenants
        self.is_reusable_repo = is_reusable_repo
        self.job_files = job_files
        self.role_files = role_files
        self.scrape_time = scrape_time

    def parse(self):
        LOGGER.info("Parsing files in repo '%s'", self.repo)

        repo_jobs = self.parse_job_files()
        repo_roles = self.parse_roles_dir()
        return repo_jobs, repo_roles

    def parse_job_files(self):
        """Check for job definitions in known zuul files."""
        repo_jobs = []
        for rel_job_file_path, job_info in self.job_files.items():
            LOGGER.debug("Checking for job definitions in %s", rel_job_file_path)
            jobs = self.parse_job_definitions(rel_job_file_path, job_info)
            LOGGER.debug("Found %d job definitions in %s", len(jobs), rel_job_file_path)
            repo_jobs.extend(jobs)
        if not repo_jobs:
            LOGGER.info("No job definitions found in repo '%s'", self.repo)
        else:
            LOGGER.info(
                "Found %d job definitions in repo '%s'", len(repo_jobs), self.repo
            )
            # LOGGER.debug(json.dumps(repo_jobs, indent=4))
        return repo_jobs

    def parse_job_definitions(self, file_path, job_info):
        try:
            jobs_yaml = yaml.load(job_info["content"], Loader=ZuulSafeLoader)
        except (ParserError, ScannerError) as e:
            LOGGER.warning("Error parsing file %s, error: %s", file_path, str(e))
            return []

        jobs = []
        for list_elem in jobs_yaml:
            job_def = list_elem.pop("job", None)
            if job_def:
                job_name = job_def["name"]
                uuid = hashlib.sha1(
                    str.encode("{}{}".format(self.repo, job_name))
                ).hexdigest()
                # Define basic job data structure
                job = ZuulJob(meta={"id": uuid})
                job.job_name = job_name
                job.repo = self.repo.name
                job.tenants = self.tenants["jobs"]
                job.private = self.repo.private
                job.scrape_time = self.scrape_time
                job.line_start = job_def["__line_start__"]
                job.line_end = job_def["__line_end__"]
                job.last_updated = last_changed_from_blame_range(
                    job.line_start, job.line_end, job_info["blame"]
                )
                job.url = self.repo.url_for_file(
                    file_path, job.line_start, job.line_end
                )

                if "description" in job_def:
                    job.description = job_def["description"]
                    try:
                        doc = render_sphinx(job.description)
                        job.description_html = doc["html"]
                        job.platforms = doc["platforms"]
                        job.reusable = doc["reusable"]
                    except SphinxBuildError as exc:
                        LOGGER.warning(
                            "Description of job '%s' could not be "
                            "converted to HTML: %s",
                            job_name,
                            exc,
                        )

                # If the repo is configured as reusable, all jobs are considered reusable
                job.reusable = self.is_reusable_repo or bool(job.reusable)

                # TODO (fschmidt): Look up the tenant.default-parent and
                # use this one over 'base' if no parent is defined.
                # If parent is explicitly set to None, we will keep it.
                job.parent = job_def.get("parent", "base")

                jobs.append(job)
        return jobs

    def parse_roles_dir(self):
        repo_roles = []

        for role_name, role_info in self.role_files.items():
            # We will build the role data structure with or without description
            uuid = hashlib.sha1(
                str.encode("{}{}".format(self.repo, role_name))
            ).hexdigest()
            role = AnsibleRole(meta={"id": uuid})
            role.role_name = role_name
            role.repo = self.repo.name
            role.tenants = self.tenants["roles"]
            role.private = self.repo.private
            role.url = self.repo.url_for_directory("roles/{}".format(role_name))
            role.scrape_time = self.scrape_time
            role.last_updated = role_info["last_changed"]

            readme_file = role_info.get("readme_file")
            if readme_file:
                # Always store the raw description (can be rendered as fallback)
                role.description = readme_file["content"]
                rendered_content = render_file(readme_file)
                if rendered_content:
                    role.description_html = rendered_content.pop("html")
                    # We might have gotten more results from the parsing (like platforms)
                    # Thus, we simply store those return values directly in the role
                    for k, v in rendered_content.items():
                        setattr(role, k, v)

            changelog_file = role_info.get("changelog_file")
            if changelog_file:
                # Always store the raw description (can be rendered as fallback)
                role.changelog = changelog_file["content"]
                rendered_content = render_file(changelog_file)
                if rendered_content:
                    role.changelog_html = rendered_content.pop("html")

            # If the repo is configured as reusable, all roles are considered reusable
            role.reusable = self.is_reusable_repo or bool(role.reusable)

            repo_roles.append(role)

        if not repo_roles:
            LOGGER.info("No role definitions found in repo '%s'", self.repo)
        else:
            LOGGER.info(
                "Found %d role definitions in repo '%s'", len(repo_roles), self.repo
            )
            # LOGGER.debug(json.dumps(repo_roles, indent=4))
        return repo_roles


# Source: https://github.com/openstack-infra/zuul-sphinx/commit/3ef1afe17ee74f5420247463652efd71e6f1e406
class ZuulSafeLoader(yaml.SafeLoader):
    def __init__(self, *args, **kwargs):
        super(ZuulSafeLoader, self).__init__(*args, **kwargs)
        self.add_multi_constructor("!encrypted/", self.construct_encrypted)

    @classmethod
    def construct_encrypted(cls, loader, tag_suffix, node):
        return loader.construct_sequence(node)

    def compose_node(self, parent, index):
        line = self.line
        node = Composer.compose_node(self, parent, index)
        # The line number where the previous token has ended (plus empty lines)
        node.__line_start__ = line + 1
        node.__line_end__ = self.line
        return node

    def construct_mapping(self, node, deep=False):
        mapping = Constructor.construct_mapping(self, node, deep=deep)
        mapping["__line_start__"] = node.__line_start__
        mapping["__line_end__"] = node.__line_end__
        return mapping
