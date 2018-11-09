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
import json
import logging
import os
import sys
from collections import namedtuple
from datetime import datetime, timedelta, timezone

import click
import github3
import zmq
from elasticsearch.exceptions import ConflictError
from elasticsearch_dsl import Q
from flask.config import Config
from tabulate import tabulate

from zubbi import default_settings
from zubbi import ZUBBI_SETTINGS_ENV
from zubbi.models import (
    AnsibleRole,
    GitRepo,
    init_elasticsearch_con,
    ZuulJob,
    ZuulTenant,
)
from zubbi.scraper.connections.github import GitHubConnection
from zubbi.scraper.exceptions import ScraperConfigurationError
from zubbi.scraper.repo_parser import RepoParser
from zubbi.scraper.repos.github import GitHubRepository
from zubbi.scraper.scraper import Scraper
from zubbi.scraper.tenant_parser import TenantParser


LOGGER = logging.getLogger(__name__)

RepoItem = namedtuple("RepoItem", "name scraped provider")


def configure_logger(verbosity):
    # Import root logger to apply the configuration to all module loggers
    from zubbi.scraper import LOGGER

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    console_handler.setFormatter(log_formatter)

    level = getattr(logging, verbosity.upper())
    environment_level = getattr(
        logging, os.environ.get("ZUBBI_VERBOSITY", verbosity).upper()
    )

    LOGGER.setLevel(min(environment_level, level))
    LOGGER.addHandler(console_handler)


# TODO (fschmidt): Move this method to the GitHubConnection class as it already
# has all the necessary parameters.
def _create_github_client(github_url, gh_con, project):
    """Create a github3 client per repo/installation."""
    token = gh_con._get_installation_key(project=project)
    if not token:
        LOGGER.warning(
            "Could not find an authentication token for '%s'. Do you "
            "have access to this repository?",
            project,
        )
        return
    gh = github3.GitHubEnterprise(github_url)
    gh.login(token=token)
    return gh


def update_tenant_configuration(
    tenant_sources_repo, tenant_sources_file, github_url, gh_con, scrape_time
):
    if tenant_sources_repo:
        gh = _create_github_client(github_url, gh_con, tenant_sources_repo)
        if not gh:
            raise ScraperConfigurationError(
                "Cannot load tenant sources from repo '{}'. No access.".format(
                    tenant_sources_repo
                )
            )

        gh_repo = GitHubRepository(tenant_sources_repo, gh)
        tenant_parser = TenantParser(sources_repo=gh_repo, scrape_time=scrape_time)
    else:
        tenant_parser = TenantParser(
            sources_file=tenant_sources_file, scrape_time=scrape_time
        )

    return tenant_parser.parse()


def _initialize_repo_cache(connections):
    LOGGER.info("Initializing repository cache")
    # Initialize Repo Cache
    repo_cache = {}

    # TODO (fschmidt): Once we have more providers, this could be done in a
    # loop, using all listed connections and add the connection's key as
    # provider in the cached_repo
    gh_con = connections["github"]

    # Get all repos from Elasticsearch
    for hit in GitRepo.search().query("match_all").scan():
        # Add 'github' type if they are listed in our github connection
        if hit.repo_name in gh_con.repos:
            repo_type = "github"
        else:
            repo_type = None
        # TODO (fschmidt): Maybe we can use this list as cache for the whole
        # scraper-webhook part.
        # This way, we could reduce the amount of operations needed for GitHub
        # and ElasticSearch
        repo_cache[hit.repo_name] = {
            "scrape_time": hit.scrape_time,
            "provider": repo_type,
        }

    return repo_cache


@click.group(invoke_without_command=True)
@click.option(
    "--verbosity",
    help="Set the active log level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
)
@click.pass_context
def main(ctx, verbosity):
    configure_logger(verbosity)

    config = Config(root_path=".")
    config.from_object(default_settings)
    config.from_envvar(ZUBBI_SETTINGS_ENV)

    ctx.obj = {"config": config}

    if ctx.invoked_subcommand is None:
        ctx.invoke(scrape)


@main.command(name="list-repos")
@click.pass_context
def list_repos(ctx):
    repos = []
    config = ctx.obj["config"]

    connections = init_connections(config)
    repo_cache = _initialize_repo_cache(connections)

    # Flatten the repo dict and format the scrape_time for console output
    for key, val in repo_cache.items():
        repos.append(
            RepoItem(
                key,
                datetime.strftime(val["scrape_time"], "%Y-%m-%dT%H:%M:%SZ"),
                val["provider"],
            )
        )

    # Sort repos by name (asc) and scrape time (desc)
    repos = sorted(repos, key=lambda x: x.name)
    repos = sorted(repos, key=lambda x: x.scraped, reverse=True)

    # Print the table
    print(
        tabulate(
            repos,
            tablefmt="orgtbl",
            headers=["Repository", "Last scraped at", "Provider"],
        )
    )


@main.command()
@click.option("--full", "-f", help="Scrape all repositories immediately", is_flag=True)
@click.option("--repo", "-r", help="Scrape only the specified repo", multiple=True)
@click.pass_context
def scrape(ctx, full, repo):

    LOGGER.info("Hello, Zubbi!")
    config = ctx.obj["config"]

    tenant_sources_repo = config.get("TENANT_SOURCES_REPO")
    tenant_sources_file = config.get("TENANT_SOURCES_FILE")

    # Fail if both are set or none of both is set
    if (
        not tenant_sources_file
        and not tenant_sources_repo
        or (tenant_sources_file and tenant_sources_repo)
    ):
        raise ScraperConfigurationError(
            "Either one of 'TENANT_SOURCES_REPO' "
            "and 'TENANT_SOURCES_FILE' must be set, "
            "but not both."
        )

    connections = init_connections(config)
    repo_cache = _initialize_repo_cache(connections)

    if full:
        scrape_full(config, connections)
    elif repo:
        scrape_full(config, connections, repos=repo)
    else:
        # Listen to ZMQ messages
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(config["ZMQ_SUB_SOCKET_ADDRESS"])
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        socket.setsockopt(zmq.RCVTIMEO, config["ZMQ_SUB_TIMEOUT"])

        while True:
            # Check for incoming messages on ZMQ
            LOGGER.debug("Checking for incoming ZMQ messages")
            try:
                event, payload = socket.recv_multipart()
                handle_event(
                    event.decode("utf-8"),
                    json.loads(payload.decode("utf-8")),
                    config,
                    connections,
                    repo_cache,
                )
            except zmq.error.Again:
                # If no message was received until the timeout, ZMQ throws
                # zmq.error.Again: Resource temporarily unavailable
                LOGGER.debug("Did not receive any ZMQ message")

            # Check if a periodic run is necessary
            LOGGER.debug("Checking for outdated repos")
            scrape_outdated(config, connections, repo_cache)


def init_connections(config):
    # Initialize global GitHub connection for GitHub App
    gh_con = GitHubConnection(config)
    gh_con.onLoad()

    # Initialize Elasticsearch connection
    init_elasticsearch_con(
        config["ES_HOST"],
        config.get("ES_USER"),
        config.get("ES_PASSWORD"),
        config.get("ES_PORT"),
    )

    # NOTE (fschmidt): We could use this one to store e.g. the Gerrit connection
    # also in here
    connections = {"github": gh_con}
    return connections


def scrape_outdated(config, connections, repo_cache):
    scrape_interval = config["FORCE_SCRAPE_INTERVAL"]
    repo_list = []
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=scrape_interval)
    # Check the repo cache for entries older than 24 hours
    for key, val in repo_cache.items():
        # TODO We should clean up repos containing 'None' providers some time
        if val["scrape_time"] < threshold and val["provider"] is not None:
            repo_list.append(key)

    if repo_list:
        LOGGER.info(
            "Found repos which weren't scraped for %d hours: %s",
            scrape_interval,
            repo_list,
        )
        scrape_repo_list(repo_list, config, connections, repo_cache)
    else:
        LOGGER.info(
            "Found no repos which weren't scraped for %d hours: %s",
            scrape_interval,
            repo_list,
        )


def scrape_full(config, connections, repos=None):
    gh_con = connections["github"]
    if repos is None:
        repos = list(gh_con.repos)
    # TODO (fschmidt): Instead of a simple string list, we should provide
    # the whole repo_cache entry containing also the provider info
    # (github, gerrit) to simplify the finding of the correct connection
    scrape_repo_list(repos, config, connections)


def scrape_repo_list(
    repo_list, config, connections, repo_cache=None, delete_only=False
):
    # Simplify the usage of a non-existing repo cache
    if repo_cache is None:
        repo_cache = {}

    scrape_time = datetime.now(timezone.utc)
    tenant_sources_repo = config.get("TENANT_SOURCES_REPO")
    tenant_sources_file = config.get("TENANT_SOURCES_FILE")
    github_url = config.get("GITHUB_URL")
    gh_con = connections["github"]

    LOGGER.info(
        "Using scraping time: %s", datetime.strftime(scrape_time, "%Y-%m-%dT%H:%M:%SZ")
    )

    # TODO (fschmidt): This should only be done once during initialization
    # and when a repo or installation changed

    # Update the installation map
    gh_con._prime_install_map()

    if not delete_only:
        # TODO (fschmidt): This should only be done once during initialization,
        # when a repo or installation changed or for a push event to the
        # TENANT_SOURCES_REPO.
        # This would also mean, that the tenant_configuration needs to be kept
        # in memory, e.g. in the TenantScraper itself (something like the prime
        # and reprime of the installations in the GitHub connection)
        # We also need to identify the repos that were added to / removed from
        # the tenant configuration in the push event.

        # Update tenant sources
        repo_map, tenant_list = update_tenant_configuration(
            tenant_sources_repo, tenant_sources_file, github_url, gh_con, scrape_time
        )

        # First, store the tenants in Elasticsearch
        LOGGER.debug(
            "Updating %d tenant definitions in Elasticsearch", len(tenant_list)
        )
        ZuulTenant.bulk_save(tenant_list)

        LOGGER.info("Scraping the following repositories: %s", repo_list)
        es_repos = []
        for repo_name in repo_list:
            # Get the tenants from the repo map. If we get no tenants, we assume
            # that the repo is not part of the tenant config.
            tenants = repo_map.get(repo_name, None)
            if tenants is None:
                LOGGER.warning(
                    "Repo '%s' is not part of our tenant sources. Skip scraping.",
                    repo_name,
                )
                continue

            # Build the data for the repo itself to be stored in Elasticsearch
            uuid = hashlib.sha1(str.encode(repo_name)).hexdigest()
            repo = GitRepo(meta={"id": uuid})
            repo.repo_name = repo_name
            repo.scrape_time = scrape_time
            es_repos.append(repo)

            cached_repo = repo_cache.setdefault(
                repo_name,
                {
                    # As we are in a GitHub event, we can just assume, the provider
                    # is github
                    "provider": "github"
                },
            )

            # Update the scrape time in cache
            cached_repo["scrape_time"] = scrape_time

            # scrape the repo if is part of the tenant config
            scrape_repo(repo_name, tenants, github_url, gh_con, scrape_time)

        # Store the information for all repos we just scraped in Elasticsearch
        LOGGER.debug("Updating %d repo definitions in Elasticsearch", len(es_repos))
        GitRepo.bulk_save(es_repos)
    else:
        LOGGER.info("Deleting the following repositories: %s", repo_list)
        # NOTE (fschmidt): Usually, this should not delete anything we just scraped.
        # Just to be sure, we will execute this only if delete_only is set.
        delete_outdated(
            scrape_time,
            [GitRepo],
            extra_filter=Q({"terms": {"repo_name.keyword": repo_list}}),
        )
        # Delete the repositories from the repo_cache
        for repo_name in repo_list:
            repo_cache.pop(repo_name, None)

    # In both cases we want to delete outdated data.
    # In case of delete_only, this will be everything!
    LOGGER.info("Deleting outdated data for the following repositories: %s", repo_list)
    delete_outdated(
        scrape_time, [AnsibleRole, ZuulJob], extra_filter=Q("terms", repo=repo_list)
    )


def scrape_repo(repo_name, tenants, github_url, gh_con, scrape_time):
    gh = _create_github_client(github_url, gh_con, repo_name)
    if not gh:
        LOGGER.warning("Skipping GitHub repo '%s'", repo_name)
        return

    gh_repo = GitHubRepository(repo_name, gh, gh_con)
    job_files, role_files = Scraper(gh_repo).scrape()

    jobs, roles = RepoParser(
        gh_repo, tenants, job_files, role_files, scrape_time
    ).parse()

    LOGGER.debug("Updating %d job definitions in Elasticsearch", len(jobs))
    ZuulJob.bulk_save(jobs)

    LOGGER.debug("Updating %d role definitions in Elasticsearch", len(roles))
    AnsibleRole.bulk_save(roles)


def delete_outdated(scrape_time, indices, extra_filter=None):
    # Delete all outdated entries in Elasticsearch
    LOGGER.info(
        "Going to delete outdated scraping results which are older than %s",
        datetime.strftime(scrape_time, "%Y-%m-%dT%H:%M:%SZ"),
    )
    for index in indices:
        try:
            deleted_docs = index.outdated_query(scrape_time, extra_filter).delete()
            LOGGER.info(
                "Deleted %d outdated %ss in Elasticsearch",
                deleted_docs.deleted,
                index.__name__,
            )
        except ConflictError:
            LOGGER.info("Deleted 0 outdated %ss in Elasticsearch", index.__name__)


# TODO (fschmidt): Maybe it's worth to move the event_* methods to a GitHubEventHandler
# class or similar. This way, we could encapsulate different events in their respective
# environment (e.g. GitHub, Gerrit, ...)
def handle_event(event, payload, config, connections, repo_cache):
    LOGGER.info("Handling event '%s'", event)
    try:
        # TODO (fschmidt): Maybe we should change this file/module to be a class
        # to get rid of this module lookup
        this_module = sys.modules[__name__]
        method = getattr(this_module, "event_{}".format(event))
    except AttributeError:
        LOGGER.warning(
            "Could not find an appropriate method to handle event '%s'", event
        )
        return

    try:
        # TODO (fschmidt): What about 'repository' events?
        # To get updates for public/private?
        # https://developer.github.com/v3/activity/events/types/#repositoryevent
        method(payload, config, connections, repo_cache)
    except Exception:
        # TODO (fschmidt): Does it make sense to catch an Exception here?
        # Could we catch anything more specific?
        LOGGER.exception("Error while handling event '%s'", event)


def event_installation(payload, config, connections, repo_cache):
    action = payload.get("action")
    installation_id = payload.get("installation", {}).get("id")
    repositories = payload.get("repositories", [])

    if action == "created":
        LOGGER.info("Scraping new installation %d", installation_id)
        # Get list of repos from the payload
        repo_names = [r["full_name"] for r in repositories]
        # Scrape them
        scrape_repo_list(repo_names, config, connections, repo_cache)

    if action == "deleted":
        LOGGER.info("Deleting data for installation %d", installation_id)
        gh_con = connections["github"]
        # Get repos for this installation from our GitHubConnection as they are
        # not listed in the payload.
        # FIXME (fschmidt): When the repo map is updated between triggering and
        # handling the event, the repo_list can no longer be retrieved from
        # the installation (which is already deleted by then).
        # As a fallback, we could search for all repos in ES which start with
        # the organization (<orga>/*)
        repositories = gh_con.get_repos_for_installation(installation_id)
        if not repositories:
            LOGGER.warning(
                "Could not retrieve repo list for installation %d. "
                "Maybe we don't have access any longer.",
                installation_id,
            )
            LOGGER.warning("Nothing to delete")
            return
        # Delete all data for those repos
        scrape_repo_list(
            repositories, config, connections, repo_cache, delete_only=True
        )

        # TODO (fschmidt): Should we remove them also from the installatino map?


def event_installation_repositories(payload, config, connections, repo_cache):
    installation_id = payload.get("installation", {}).get("id")
    repos_added = payload.get("repositories_added")
    repos_removed = payload.get("repositories_removed")

    project_name = payload.get("repository", {}).get("full_name")
    print(installation_id)
    print(project_name)

    # TODO validate installation id from payload against installation map?
    # If they do not match, we might have missed an installation event and
    # should update our installation map

    # Scrape each added repo
    if repos_added is not None:
        LOGGER.info(
            "Scraping %d new repositories for installation %d",
            len(repos_added),
            installation_id,
        )
        # Get list of repos from the payload
        repo_names = [r["full_name"] for r in repos_added]
        # Scrape them
        scrape_repo_list(repo_names, config, connections, repo_cache)

    # Just delete the data for these repos
    if repos_removed is not None:
        LOGGER.info(
            "Deleting data from %d repositories for installation %d",
            len(repos_removed),
            installation_id,
        )
        # Get list of repos from the payload
        repo_names = [r["full_name"] for r in repos_added]
        # Delete all data for those repos
        scrape_repo_list(repo_names, config, connections, repo_cache, delete_only=True)


def event_push(payload, config, connections, repo_cache):
    repo_name = payload.get("repository", {}).get("full_name")
    # installation_id = payload.get('installation', {}).get('id')
    ref = payload.get("ref")
    # old_ref = payload.get('before')
    # new_ref = payload.get('after')
    # commits = payload.get('commits')

    gh_con = connections["github"]

    repo_info = gh_con.installation_map.get(repo_name)
    default_branch = repo_info["default_branch"]

    # TODO validate installation id from payload against installation map?
    # If they do not match, we might have missed an installation event and
    # should update our installation map

    parts = ref.split("/", 2)
    branch = parts[2]
    if branch != default_branch:
        LOGGER.info(
            "Push event contains ref %s, but default branch is %s. "
            "Won't handle event for repo %s.",
            ref,
            default_branch,
            repo_name,
        )
        return

    LOGGER.info("Handling push event for repo %s with ref %s", repo_name, ref)

    scrape_repo_list([repo_name], config, connections, repo_cache)


if __name__ == "__main__":
    main()
