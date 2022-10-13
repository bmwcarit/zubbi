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
import time
from collections import namedtuple
from datetime import datetime, timedelta, timezone

import click
import zmq
from elasticsearch.exceptions import ConflictError
from elasticsearch_dsl import Q
from flask.config import Config
from tabulate import tabulate

from zubbi import default_settings
from zubbi import ZUBBI_SETTINGS_ENV
from zubbi.models import (
    AnsibleRole,
    get_elasticsearch_parameters_from_config,
    GitRepo,
    init_elasticsearch_con,
    ZuulJob,
    ZuulTenant,
)
from zubbi.scraper.connections.gerrit import GerritConnection
from zubbi.scraper.connections.git import GitConnection
from zubbi.scraper.connections.github import GitHubConnection
from zubbi.scraper.exceptions import ScraperConfigurationError
from zubbi.scraper.repo_parser import RepoParser
from zubbi.scraper.repos.gerrit import GerritRepository
from zubbi.scraper.repos.git import GitRepository
from zubbi.scraper.repos.github import GitHubRepository
from zubbi.scraper.scraper import Scraper
from zubbi.scraper.tenant_parser import TenantParser


LOGGER = logging.getLogger(__name__)

CONNECTIONS = {
    "git": GitConnection,
    "github": GitHubConnection,
    "gerrit": GerritConnection,
}
REPOS = {"git": GitRepository, "github": GitHubRepository, "gerrit": GerritRepository}
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


def _initialize_tenant_parser(tenant_sources_repo, tenant_sources_file, connections):
    if tenant_sources_repo:
        # Config entry must be in format <connection_name>:<repo>
        con_name, repo_name = tenant_sources_repo.split(":", 1)
        con = connections.get(con_name)
        if not con:
            raise ScraperConfigurationError(
                f"Cannot load tenant sources from repo '{repo_name}'. "
                f"Specified connection '{con_name}' is not avilable."
            )
        provider = con.provider
        repo_class = REPOS.get(provider)
        if not repo_class:
            raise ScraperConfigurationError(
                f"Cannot load tenant sources from repo '{repo_name}'. "
                f"Unknown connection provider '{provider}'."
            )

        repo = repo_class(repo_name, con)
        tenant_parser = TenantParser(sources_repo=repo)
    else:
        tenant_parser = TenantParser(sources_file=tenant_sources_file)

    tenant_parser.parse()
    return tenant_parser


def _initialize_repo_cache():
    """Initialize the repository cache used for scraping.

    Retrieves a list of repositories with their provider and last scraping time
    from Elasticsearch.
    This list can be used to check which repos need to be scraped (e.g. after
    a specific amount of time).
    """
    LOGGER.info("Initializing repository cache")
    # Initialize Repo Cache
    repo_cache = {}

    # Get all repos from Elasticsearch
    for hit in GitRepo.search().query("match_all").scan():
        # TODO (fschmidt): Maybe we can use this list as cache for the whole
        # scraper-webhook part.
        # This way, we could reduce the amount of operations needed for GitHub
        # and ElasticSearch
        repo_cache[hit.repo_name] = hit.to_dict(skip_empty=False)

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

    # Load the configurations from file
    config = Config(root_path=".")
    config.from_object(default_settings)
    config.from_envvar(ZUBBI_SETTINGS_ENV)

    # Validate the configuration
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

    # Store the config in click's context object to be available for subcommands
    ctx.obj = {"config": config}

    if ctx.invoked_subcommand is None:
        ctx.invoke(scrape)


@main.command(name="list-repos")
@click.pass_context
def list_repos(ctx):
    repos = []

    config = ctx.obj["config"]
    tenant_sources_repo = config.get("TENANT_SOURCES_REPO")
    tenant_sources_file = config.get("TENANT_SOURCES_FILE")

    # Initialize objects that are needed by all subcommands
    connections = init_connections(ctx.obj["config"])
    repo_cache = _initialize_repo_cache()
    tenant_parser = _initialize_tenant_parser(
        tenant_sources_repo, tenant_sources_file, connections
    )

    for key in tenant_parser.repo_map.keys():
        # Get the corresponding data from the repo cache, flatten the repo dict
        # and format the scrape_time for console output.
        cached_repo = repo_cache.get(key)
        if cached_repo is not None:
            list_item = RepoItem(
                key,
                datetime.strftime(cached_repo["scrape_time"], "%Y-%m-%dT%H:%M:%SZ"),
                cached_repo["provider"],
            )
        else:
            list_item = RepoItem(key, "<not scraped yet>", "<unknown>")

        repos.append(list_item)

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

    # Initialize objects that are needed by all subcommands
    connections = init_connections(ctx.obj["config"])
    reusable_repos = ctx.obj["config"].get("REUSABLE_PROJECTS", [])
    repo_cache = _initialize_repo_cache()
    tenant_parser = _initialize_tenant_parser(
        tenant_sources_repo, tenant_sources_file, connections
    )

    if full:
        scrape_full(connections, reusable_repos, tenant_parser)
    elif repo:
        scrape_full(connections, reusable_repos, tenant_parser, repos=repo)
    else:
        # Listen to ZMQ messages
        socket_addr = config.get("ZMQ_SUB_SOCKET_ADDRESS")
        timeout = config.get("ZMQ_SUB_TIMEOUT")
        socket = create_zmq_socket(socket_addr, timeout)

        while True:
            # Check if a periodic run is necessary
            LOGGER.debug("Checking for outdated repos")
            scrape_outdated(
                config, connections, reusable_repos, tenant_parser, repo_cache
            )

            # Listen to ZMQ messages (if configured) or wait
            if socket is None:
                LOGGER.debug(
                    "No ZMQ socket configured. Just going to wait for %d seconds.",
                    timeout,
                )
                time.sleep(timeout)
            else:
                # Check for incoming messages on ZMQ
                LOGGER.debug("Checking for incoming ZMQ messages")
                try:
                    event, payload = socket.recv_multipart()
                    handle_event(
                        event.decode("utf-8"),
                        json.loads(payload.decode("utf-8")),
                        connections,
                        reusable_repos,
                        tenant_parser,
                        repo_cache,
                    )
                except zmq.error.Again:
                    # If no message was received until the timeout, ZMQ throws
                    # zmq.error.Again: Resource temporarily unavailable
                    LOGGER.debug("Did not receive any ZMQ message")


def create_zmq_socket(socket_addr, timeout):
    socket = None
    if socket_addr and timeout:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(socket_addr)
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        # Timeout is in seconds, but ZMQ uses milliseconds
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
    return socket


def init_connections(config):
    # Initialize Elasticsearch connection
    es_config = get_elasticsearch_parameters_from_config(config)
    init_elasticsearch_con(**es_config)

    connections = {}
    for con_name, con_data in config["CONNECTIONS"].items():
        # Look up the connection provider and initialize it with the remaining
        # config keys. Abstraction for e.g. the following:
        # gh_con = GitHubConnection(**con_data)
        # connections['github'] = gh_con
        provider = con_data.pop("provider")
        con_class = CONNECTIONS.get(provider)
        if not con_class:
            raise ScraperConfigurationError(
                "Could not init connection '{}'. Specified provider '{}' is not"
                " available.".format(con_name, provider)
            )

        con = con_class(**con_data)
        con.init()
        connections[con_name] = con
    return connections


def scrape_outdated(config, connections, reusable_repos, tenant_parser, repo_cache):
    scrape_interval = config["FORCE_SCRAPE_INTERVAL"]
    repo_list = []
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=scrape_interval)
    # Check the repo cache for entries older than 24 hours
    for key, val in repo_cache.items():
        # TODO We should clean up repos containing 'None' providers some time
        if val["scrape_time"] < threshold and val.get("provider") is not None:
            repo_list.append(key)

    if repo_list:
        LOGGER.info(
            "Found repos which weren't scraped for %d hours: %s",
            scrape_interval,
            repo_list,
        )
        scrape_repo_list(
            repo_list, connections, reusable_repos, tenant_parser, repo_cache=repo_cache
        )
    else:
        LOGGER.info(
            "Found no repos which weren't scraped for %d hours: %s",
            scrape_interval,
            repo_list,
        )


def scrape_full(connections, reusable_repos, tenant_parser, repos=None):
    if repos is None:
        # If we don't have any repos provided, we get all available once from the
        # tenant configuration
        tenant_parser.parse()
        repo_map = tenant_parser.repo_map
        tenant_list = tenant_parser.tenants
        scrape_time = datetime.now(timezone.utc)
        _scrape_repo_map(
            repo_map,
            tenant_list,
            connections,
            reusable_repos,
            scrape_time,
            repo_cache={},
            delete_only=False,
        )
    else:
        scrape_repo_list(repos, connections, reusable_repos, tenant_parser)


def scrape_repo_list(
    repo_list,
    connections,
    reusable_repos,
    tenant_parser,
    repo_cache=None,
    delete_only=False,
):
    scrape_time = datetime.now(timezone.utc)

    # Simplify the usage of a non-existing repo cache
    if repo_cache is None:
        repo_cache = {}

    # Keep track on repositories that are no longer part of our tenant config
    # and thus should be deleted from Elasticsearch. Otherwise, Zubbi will loop
    # over them each time once they become outdated (older than 24 hours).
    invalid_repo_map = {}

    # Update tenant sources
    # TODO (fschmidt): This should not be necessary for each scraping. But, as we
    # don't have a mechanism yet to filter for the necessary events, we keep it
    # like this.
    tenant_parser.parse()
    repo_map = tenant_parser.repo_map
    tenant_list = tenant_parser.tenants
    filtered_repo_map = {}
    # Get the relevant repositories from the tenant parser's repo map.
    # Repos which are not part of them won't be scraped.
    for repo_name in repo_list:
        # Get the tenants from the repo map. If we get no tenants, we assume
        # that the repo is not part of the tenant config.
        repo_data = repo_map.get(repo_name, None)
        if repo_data is None:
            LOGGER.warning(
                "Repo '%s' is not part of our tenant sources. Skip scraping.", repo_name
            )
            invalid_repo_map[repo_name] = None
        else:
            # TODO Simplify this with dict/list comprehension
            filtered_repo_map[repo_name] = repo_data

    if invalid_repo_map:
        LOGGER.info(
            "The following repositories are no longer part of our tenant "
            "sources and will be deleted: %s",
            invalid_repo_map.keys(),
        )
        _scrape_repo_map(
            # TODO (felix): It would be simpler if we could provide a list here
            # as - in case the delete_only is set - we will only extract the
            # keys from the map and delete all data for those repositories.
            # Maybe we could check sometime why the split between
            # _scrape_repo_map and _scrape_repo_list was necessary. IIRC I did
            # that mainly to simplify the call via command line (when repos are
            # specified as arguments).
            invalid_repo_map,
            tenant_list,
            connections,
            reusable_repos,
            scrape_time,
            repo_cache,
            delete_only=True,
        )

    if not filtered_repo_map:
        LOGGER.info("Repo list is empty, nothing to scrape.")
        return

    return _scrape_repo_map(
        filtered_repo_map,
        tenant_list,
        connections,
        reusable_repos,
        scrape_time,
        repo_cache,
        delete_only,
    )


def _scrape_repo_map(
    repo_map, tenants, connections, reusable_repos, scrape_time, repo_cache, delete_only
):
    # TODO It would be great if the tenant_list contains only the relevant tenants based
    # on the repository map (or whatever is the correct source). In other words:
    # It should only contain the tenants which are really "updated".

    tenant_list = []
    for tenant_name in tenants:
        # Build the tenant data for Elasticsearch
        uuid = hashlib.sha1(str.encode(tenant_name)).hexdigest()
        tenant = ZuulTenant(meta={"id": uuid})
        tenant.tenant_name = tenant_name
        tenant.scrape_time = scrape_time
        tenant_list.append(tenant)

    # Simplify the list of repos for log output and keyword match in Elasticsearch
    # NOTE (fschmidt): Elasticsearch can only work with lists
    repo_list = list(repo_map.keys())

    LOGGER.info(
        "Using scraping time: %s", datetime.strftime(scrape_time, "%Y-%m-%dT%H:%M:%SZ")
    )

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

        # First, store the tenants in Elasticsearch
        LOGGER.info("Updating %d tenant definitions in Elasticsearch", len(tenant_list))
        ZuulTenant.bulk_save(tenant_list)

        LOGGER.info("Scraping the following repositories: %s", repo_list)

        for repo_name, repo_data in repo_map.items():
            # Extract the data from the repo_data
            tenants = repo_data["tenants"]
            connection_name = repo_data["connection_name"]

            cached_repo = repo_cache.setdefault(repo_name, repo_data)

            # Update the scrape time in cache
            cached_repo["scrape_time"] = scrape_time

            # Initialize the repository for scraping
            con = connections.get(connection_name)
            if not con:
                LOGGER.error(
                    "Checkout of repo '%s' failed. No connection named '%s' found. "
                    "Please check your configuration file.",
                    repo_name,
                    connection_name,
                )
                # NOTE (felix): Remove the repo from the repo_list, so the outdated
                # data (which would be all data in this case) won't be deleted.
                repo_list.remove(repo_name)
                continue
            provider = con.provider
            repo_class = REPOS.get(provider)
            repo = repo_class(repo_name, con)

            # Check if the repo was created successfully, if not, skip it.
            # Possible reasons are e.g: No access (via GitHub app or Gerrit user),
            # Clone/checkout failures for plain git repos or similar.
            if not repo._repo:
                LOGGER.error(
                    "Repo '%s' could not be initialized. Skip scraping.", repo_name
                )
                continue

            # Build the data for the repo itself to be stored in Elasticsearch
            uuid = hashlib.sha1(str.encode(repo_name)).hexdigest()
            es_repo = GitRepo(meta={"id": uuid})
            es_repo.repo_name = repo_name
            es_repo.scrape_time = scrape_time
            es_repo.provider = provider

            # scrape the repo if is part of the tenant config
            scrape_repo(repo, tenants, reusable_repos, scrape_time)

            # Store the information for the repository itself, if it was scraped successfully
            LOGGER.info("Updating repo definition for '%s' in Elasticsearch", repo_name)
            GitRepo.bulk_save([es_repo])
    else:
        # Delete the repositories from the repo_cache
        for repo_name in repo_list:
            repo_cache.pop(repo_name, None)

    # In both cases we want to delete outdated data.
    # In case of delete_only, this will be everything!
    # NOTE (felix): In case of a config error, the repo is removed from this list
    LOGGER.info("Deleting outdated data for the following repositories: %s", repo_list)
    delete_outdated(
        scrape_time, [AnsibleRole, ZuulJob], extra_filter=Q("terms", repo=repo_list)
    )

    LOGGER.info("Deleting the following repositories (only if outdated): %s", repo_list)
    # NOTE (fschmidt): Usually, this should not delete anything we just scraped.
    delete_outdated(
        scrape_time,
        [GitRepo],
        extra_filter=Q({"terms": {"repo_name.keyword": repo_list}}),
    )


def scrape_repo(repo, tenants, reusable_repos, scrape_time):
    job_files, role_files = Scraper(repo).scrape()

    is_rusable_repo = repo.repo_name in reusable_repos
    jobs = []
    roles = []
    try:
        jobs, roles = RepoParser(
            repo, tenants, job_files, role_files, scrape_time, is_rusable_repo
        ).parse()
    except Exception:
        LOGGER.exception("Unable to parse job or role definitions in repo '%s'", repo)

    LOGGER.info("Updating %d job definitions in Elasticsearch", len(jobs))
    ZuulJob.bulk_save(jobs)

    LOGGER.info("Updating %d role definitions in Elasticsearch", len(roles))
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
def handle_event(
    event, payload, connections, reusable_repos, tenant_parser, repo_cache
):
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
        method(payload, connections, reusable_repos, tenant_parser, repo_cache)
    except Exception:
        # TODO (fschmidt): Does it make sense to catch an Exception here?
        # Could we catch anything more specific?
        LOGGER.exception("Error while handling event '%s'", event)


def event_installation(payload, connections, reusable_repos, tenant_parser, repo_cache):
    action = payload.get("action")
    installation_id = payload.get("installation", {}).get("id")
    repositories = payload.get("repositories", [])

    LOGGER.info(
        "Handling installation event with action '%s' for installation %d",
        action,
        installation_id,
    )

    if action == "created":
        LOGGER.info("Scraping repos for new installation %d", installation_id)
        # Get list of repos from the payload
        repo_names = [r["full_name"] for r in repositories]
        # Scrape them
        scrape_repo_list(
            repo_names,
            connections,
            reusable_repos,
            tenant_parser,
            repo_cache=repo_cache,
        )

    if action == "deleted":
        LOGGER.info("Deleting data for installation %d", installation_id)
        # TODO (felix) Get the right connection from the configuration based on what?
        # The provider? The github url? Both?
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
                "Maybe we don't have access any longer."
                "Nothing to delete",
                installation_id,
            )
            return
        # Delete all data for those repos
        scrape_repo_list(
            repositories,
            connections,
            reusable_repos,
            tenant_parser,
            repo_cache=repo_cache,
            delete_only=True,
        )

        # TODO (fschmidt): Should we remove them also from the installatino map?


def event_installation_repositories(
    payload, connections, reusable_repos, tenant_parser, repo_cache
):
    installation_id = payload.get("installation", {}).get("id")
    repos_added = payload.get("repositories_added")
    repos_removed = payload.get("repositories_removed")

    LOGGER.info(
        "Handling installation_repositories event for installation %d", installation_id
    )

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
        scrape_repo_list(
            repo_names,
            connections,
            reusable_repos,
            tenant_parser,
            repo_cache=repo_cache,
        )

    # Just delete the data for these repos
    if repos_removed is not None:
        LOGGER.info(
            "Deleting data from %d repositories for installation %d",
            len(repos_removed),
            installation_id,
        )
        # Get list of repos from the payload
        repo_names = [r["full_name"] for r in repos_removed]
        # Delete all data for those repos
        scrape_repo_list(
            repo_names,
            connections,
            reusable_repos,
            tenant_parser,
            repo_cache=repo_cache,
            delete_only=True,
        )


def event_push(payload, connections, reusable_repos, tenant_parser, repo_cache):
    repo_name = payload.get("repository", {}).get("full_name")
    LOGGER.info("Handling push event for repo '%s'", repo_name)
    # NOTE (felix): We could use the installation_id later on, to update the
    # installation map only for this installation.
    # installation_id = payload.get('installation', {}).get('id')
    ref = payload.get("ref")

    # TODO (felix) Get the right connection from the configuration based on what?
    # The provider? The github url? Both?
    gh_con = connections["github"]

    repo_info = gh_con.installation_map.get(repo_name)
    if not repo_info:
        # If the repo is not part of our installation map, we might have missed the create/add event.
        # Thus, we could reinit the GitHub connection and try it again
        # TODO (felix): re-init for this installation only?
        LOGGER.info(
            "Repo '%s' is not part of our installation map, we might have missed an event. "
            "Reinitialising installation map",
            repo_name,
        )
        gh_con._prime_install_map()
        repo_info = gh_con.installation_map.get(repo_name)
        if not repo_info:
            LOGGER.error(
                "Repo '%s' still not part of our installation map, something went wrong. Skip scraping."
            )
            return

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

    scrape_repo_list(
        [repo_name], connections, reusable_repos, tenant_parser, repo_cache=repo_cache
    )


if __name__ == "__main__":
    main()
