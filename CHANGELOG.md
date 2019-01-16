# Changelog

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
