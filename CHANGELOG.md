# Changelog

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
