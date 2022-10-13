# Changelog

## 2.4.6

### Fixes
- Filter job files for *.yaml extension before parsing to avoid yaml parser
  errors. So far, Zubbi was parsing all files (including e.g. a README.md file)
  within the jobs directory which made the parser fail.
- Make the RepoParser more robust against files with invalid yaml content. In
  case an error occurs during job or role parsing this should now only affect
  the current repository but not the whole scraper run.

## 2.4.5

### Fixes
- Remove the noreferrer header from the zubbi repository link in the footer
  to not leak internal URLs.
- Use pagination when fetching installation ids from GitHub. So far, Zubbi
  only fetched the first 50 installations.
- Ignore job file if there is syntax error when parsing yaml content.

## 2.4.4

### Fixes
- Fixed a bug that resulted in an internal server error when using a search
  query that contains a '/' in zubbi-web.

## 2.4.3

### Fixes
- Fixed a bug that made the zubbi-scraper crash when a zuul config directory
  contained not only files but a nested directory structure. Those config
  directories are now scraped recursively.
- Fixed a bug that made zubbi-scraper crash on startup if the TENANT_SOURCES_REPO
  setting referenced an unknown connection.

## 2.4.2

### Fixes
- Fixed a GraphQL query which was relying on a master branch being present in
  the repository.

## 2.4.1

### Fixes
- How-to page is updated with description of supported_os and reusable directives.

## 2.4.0

### New Features
- **UI:** Improve search results ordering. The search results will be ordered by
  the priority of the fields matching the query. The priority is like the following:
  name -> description -> tenant/repo.
- **Scraper** Projects(repositories) can be configured as "reusable" in settings.cfg.
  When A repository is configured as "reusable", all jobs and roles scraped from this
  repository are marked as "reusable".

## 2.3.0

### New Features
- **Scraper:** Support marking roles and jobs as "reusable". It parses the directive
  in role's README file and job's description and store it in Elasticsearch.
- **UI:** Search result will display roles and jobs that are marked as "reusable"
  on top, and highlight them.

## 2.2.2

### General
- Updated dependencies to newest versions

## 2.2.1

### Fixes
- Fixed a bug where the delete outdated query never matched repositories on
  Github. To fix this behaviour, an additional repo_name.keyword field was
  introduced in the git-repos index.
- The connections are now first initialized when a valid scraper command is
  invoked. Thus, running `zubbi-scraper --help` or providing wrong command line
  arguments should directly run and return without unnecessarily initializing
  the connections to Github, Gerrit and Elasticsearch.

## 2.2.0

### General
- Updated dependencies to newest versions

## 2.1.2

### Fixes
- **Elasticsearch:** If an index_prefix is provided, but empty, it will be ignored.

## 2.1.1

### Fixes
- **Scraper:** Unfortunately, the scraper wasn't aware of the new Elasticsearch
  configuration format and the SSL options.

## 2.1.0

### New Features
- **Elasticsearch:** Support SSL options for the Elasticsearch connection. For a
  list of available options, take a look at the settings.cfg.example file.

### Deprecated
- **Configuration:** Changed the format on how to specify the Elasticsearch
  connection in the config file to a single dictionary (like for CONNECTIONS).
  The old format (prefixing everything with "ES_") is still supported but will
  be removed in future versions. Please see the settings.cfg.example for details
  to the new format.

## 2.0.0

### New Features
- **Scraper:** Update repo information in Elasticsearch directly after scraping.
  Previously, we updated the information for all scraped repositories in one go to
  reduce the amount of requests sent to Elasticsearch. However, this had the drawback,
  that none of the repo information was updated if scraping any of the repositories
  failed.

### Fixes
- **Scraper:** Fix a bug were the scraper was still trying to check out GitHub
  repositories, although it didn't have a valid access token.
- **Scraper:** Don't fail when trying to split the owner from an invalid GitHub
  repository names. Actually, the wrong name comes from a bug in the tenant scraper
  which should be fixed in a future release. But for now, it's a good idea to make
  this part more robust.

### Backwards incompatible changes
- **Elasticsearch:** Zubbi 2.x.x is only compatible with Elasticsearch major version 7.

## 1.3.0

### New Features
- **Experimental:** You can set an `ES_INDEX_PREFIX` in the `settings.cfg` file to
  prefix all Elasticsearch indices with a custom value. This could be useful to avoid
  name clashes if indices with the same name are already used by another part of the
  system.

## 1.2.0

### New Features
- **UI:** Autofocus the search field on index page. You can now visit Zubbi and
  directly start typing.
- **UI:** Show "last update" timestamps for jobs and roles in search results.
- **Extensions:** Allow custom tabs/contents on details page. When extending Zubbi,
  someone can now add new tabs (in addition to the already existing 'Description'
  and 'Changelog').

### Fixes
- **UI:** Use rendered description in search result cards to hide unparsable
  Sphinx links.

## 1.1.0

### New Features
- Add support for `gitweb` and `cgit` as Gerrit web front-ends. Those are
  necessary to build the correct URLs which are pointing to a job's or role's
  definition file/directory in Gerrit.

### Fixes
- Make Gerrit credentials really optional

## 1.0.0

### New Features
- **Gerrit support:** Zubbi now supports scraping of Gerrit repositories. In
  contrary to GitHub, most of the necessary operations (check out files, list
  directories) are done via `gitpython` as the Gerrit API does not support all
  use cases. This allows the usage of Git repositories that are independent of
  GitHub or Gerrit.
- **Quickstart Guide:** The README file now contains a quickstart section,
  explaining how to set up zubbi-web and zubbi-scraper with a local Elasticsearch
  instance and get a first set of data.

### Fixes
- Reactivate markdown rendering after breaking change in `readme_renderer`
  dependency.
