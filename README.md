![Welcome to the Zuul Building Blocks Index](https://github.com/bmwcarit/zubbi/raw/master/.github/zubbi-index.png)

<br/>

The Zuul Building Blocks Index (aka Zubbi) makes it easy to search for available
jobs and roles ("Building Blocks") within a [Zuul](https://zuul-ci.org/docs/zuul/)
based CI system - even if they are spread over multiple tenants or repositories.

---

*Contents:* **[Requirements](#requirements)** |
**[Architecture](#architecture)** |
**[Setup & Configuration](#setup--configuration)** |
**[Development](#development)**

---

## Requirements
- Elasticsearch
- GitHub + GitHub App

## Architecture
![zubbi-architecture](https://github.com/bmwcarit/zubbi/raw/master/.github/zubbi-architecture.png)

Zubbi consists of two parts, **zubbi web** and **zubbi scraper**. It uses
**Elasticsearch** as storage backend and needs **GitHub repositories** as
source for job and role definitions.

### Zubbi web
A web frontend based on Flask that reads the data from Elasticsearch. It allows
searching for roles and jobs used within the CI system and shows the results
including their documentation, last updates, changelog and some additional meta
data.

### Zubbi scraper
A Python application that scrapes GitHub repositories, searches for job and
role definitions in specific files and stores them in Elasticsearch.

## Setup & Configuration
Both components read their configuration from the file path given via the
`ZUBBI_SETTINGS` environment variable.

```shell
$ export ZUBBI_SETTINGS=$(pwd)/settings.cfg
```

An example with all available settings can be found in `settings.cfg.example`.

### GitHub App
To be able to scrape the necessary repositories from GitHub, you need to create a
GitHub App with the following permissions:

```yaml
Repository contents: Read-only
Repository metadata: Read-only
```

To activate GitHub webhooks, you have to provide a Weebhook URL pointing to
the `/api/webhook` endpoint of your Zubbi Web installation. The generated Webhook
secret must be specified in the `GITHUB_WEBHOOK_SECRET` setting.

If you are unsure about how to set up a GitHub App, take a look at the
[official guide](https://developer.github.com/apps/building-github-apps/creating-a-github-app/).

Once you have successfully created your GitHub App, you can adapt the following
values in your `settings.cfg` accordingly:

```ini
GITHUB_APP_ID = <your_github_app_id>
GITHUB_APP_KEY = '<path_to_keyfile>'
GITHUB_WEBHOOK_SECRET = '<secret>'
```

### Tenant Configuration
Zubbi needs to know which projects contain the job and role definitions that
are used inside the CI system. To achieve this, it uses Zuul's
[tenant configuration](https://zuul-ci.org/docs/zuul/admin/tenants.html).
Usually, this tenant configuration is stored in a file that must be specified
in the `settings.cfg`, but it could also come from a repository.

```ini
# Use only one of the following, not both
TENANT_SOURCES_REPO = '<orga>/<repo>'
TENANT_SOURCES_FILE = '<path_to_the_yaml_file>'
```

### Elasticsearch Connection
The Elasticsearch connection can be configured in the `settings.cfg` file like
the following:

```ini
ES_HOST = '<elasticsearch_host>'
ES_PORT = 9200
ES_USER = 'user'
ES_PASSWORD = 'password'
```

## Development

Prerequisites: Python 3.6, [Tox](https://tox.readthedocs.io/en/latest/) and
[Pipenv](https://docs.pipenv.org/) installed

To start the basic Zubbi web application:
```shell
$ pipenv shell
$ export FLASK_APP=zubbi
$ export FLASK_DEBUG=true
$ flask run
```

The Zubbi scraper supports to different modes: `periodic` (default) and `immediate`.
To start the scraper in periodic mode, simply run:

```shell
$ ./zubbi-scraper scrape
```
This should also scrape all necessary repositories for the first time.

To immediately scrape one or more repositories (e.g. to update specific
repositories), mostly used for development, run:

```shell
# Scrape one or more repositories
$ ./zubbi-scraper scrape --repo 'orga1/repo1' --repo 'orga1/repo2'

# Scrape all repositories
$ ./zubbi-scraper scrape --full
```

Additionally, the scraper provides a `list-repos` command to list all
available repositories and when they were scraped the last time:
```shell
$ ./zubbi-scrape list-repos
```

### Running tests & static checks

Tests are run using tox:

```shell
$ tox
```

### Installing & updating dependencies

Test dependencies should be installed as development dependencies:

```shell
$ pipenv install --dev my-test-dependency
```

To update the dependencies to the latest version or after a new dependency was
installed you have to run `tox -e update-requirements` and commit the changed
Pipenv and requirements files

### Building the syntax highlighting stylesheet with pygments

In case you want to rebuild the syntax highlighting stylesheet (e.g. to try
out another highlighting style) you can run the following command:
```shell
$ pygmentize -S default -f html -a .highlight > zubbi/static/pygments.css
```

*Happy coding!*
