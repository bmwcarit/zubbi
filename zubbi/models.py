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

import jinja2
from elasticsearch.helpers import bulk
from elasticsearch_dsl import (
    Completion,
    connections,
    Date,
    Document,
    Integer,
    Q,
    Search,
    Text,
)


DEFAULT_ES_PORT = 9200
DEFAULT_SUGGEST_SIZE = 5


class ZubbiDoc(Document):
    """All documents which are scraped by Zubbi and stored in Elasticsearch."""

    scrape_time = Date(default_timezone="UTC")

    @classmethod
    def outdated_query(cls, timestamp, extra_filter=None):
        extra_filter = extra_filter or []

        return (
            cls.search()
            .query("bool", filter=extra_filter)
            .filter("range", scrape_time={"lt": timestamp})
        )

    # Helper method as mentioned in
    # https://github.com/elastic/elasticsearch-dsl-py/issues/403
    @classmethod
    def bulk_save(cls, docs):
        objects = (d.to_dict(include_meta=True) for d in docs)
        client = connections.get_connection()
        return bulk(client, objects)


class ZuulTenant(ZubbiDoc):
    tenant_name = Text()

    class Index:
        name = "zuul-tenants"


class GitRepo(ZubbiDoc):
    repo_name = Text()
    provider = Text()

    class Index:
        name = "git-repos"


class Block(ZubbiDoc):
    name_suggest = Completion(
        contexts=[
            {"name": "private", "type": "category", "path": "private"},
            {"name": "tenants", "type": "category", "path": "tenants"},
        ]
    )
    repo = Text(analyzer="whitespace")
    tenants = Text(multi=True, analyzer="whitespace")
    # NOTE (fschmidt): Elasticsearch does not support context suggestion for
    # Boplean fields. As we are using the private flag to filter the auto-
    # completion results, this must be Text.
    private = Text()
    url = Text()
    description = Text(analyzer="whitespace")
    description_html = Text()
    platforms = Text(multi=True, analyzer="whitespace")
    last_updated = Date(default_timezone="UTC")

    @staticmethod
    def suggest_field():
        return "name_suggest"

    @property
    def has_html_description(self):
        return bool(self.description_html)

    @property
    def has_html_changelog(self):
        return bool(self.changelog_html)

    @property
    def description_rendered(self):
        return self._renderable_field(self.description_html, self.description)

    def _renderable_field(self, html, raw):
        if html:
            return jinja2.Markup(html)
        elif raw:
            return jinja2.Markup("<pre>{}</pre>".format(jinja2.escape(raw)))


class AnsibleRole(Block):
    # NOTE (fschmidt): We have to store the name as 'role_name' in the result,
    # so we can use it for aggregation in Elasticsearch later on.
    role_name = Text(analyzer="whitespace")
    changelog = Text(analyzer="whitespace")
    changelog_html = Text()

    class Index:
        name = "ansible-roles"

    @property
    def name(self):
        return self.role_name

    @property
    def changelog_rendered(self):
        return self._renderable_field(self.changelog_html, self.changelog)

    @classmethod
    def bulk_save(cls, docs):
        for doc in docs:
            doc.name_suggest = doc.role_name
        return super().bulk_save(docs)


class ZuulJob(Block):
    # NOTE (fschmidt): We have to store the name as 'job_name' in the result,
    # so we can use it for aggregation in Elasticsearch later on.
    job_name = Text(analyzer="whitespace")
    parent = Text(analyzer="whitespace")
    line_start = Integer()
    line_end = Integer()

    class Index:
        name = "zuul-jobs"

    @property
    def name(self):
        return self.job_name

    def save(self, **kwargs):
        # Make sure that the name suggestion contains the name
        self.name_suggest = self.job_name
        return super().save(**kwargs)


class BlockSearch(Search):
    def __init__(self, index=None, doc_type=None, block_class=None, **kwargs):
        super().__init__(
            index=self._select_index(index, block_class),
            doc_type=self._select_doc_type(doc_type, block_class),
            **kwargs
        )

    @staticmethod
    def _select_index(index, block_class):
        if index:
            return index
        if block_class is not None:
            return block_class._default_index()
        return [AnsibleRole._default_index(), ZuulJob._default_index()]

    @staticmethod
    def _select_doc_type(doc_type, block_class):
        if doc_type:
            return doc_type
        if block_class is not None:
            return [block_class]
        return [AnsibleRole, ZuulJob]

    def search_query(self, query, fields, exact=False, extra_filter=None):
        # Elasticsearch cannot work with a set, only with list
        fields = list(fields)
        if exact:
            search_query = Q("multi_match", query=query, fields=fields)
        else:
            query_string = "*{}*".format(query)
            search_query = Q("query_string", query=query_string, fields=fields)

        extra_filter = extra_filter or []

        return self.query("bool", filter=extra_filter, must=search_query)

    def detail_query(self, block_name, repo, extra_filter=None):
        extra_filter = extra_filter or []
        detail_query = [
            Q("query_string", query=block_name, fields=["job_name", "role_name"]),
            Q("match", repo=repo),
        ]
        return self.query("bool", filter=extra_filter, must=detail_query)

    def suggest_query(
        self, text, name="suggester", size=DEFAULT_SUGGEST_SIZE, contexts=None
    ):
        contexts = contexts or {}
        return self.suggest(
            name,
            text,
            completion={
                "field": Block.suggest_field(),
                "size": size,
                "contexts": contexts,
            },
        )


def role_type(item):
    return isinstance(item, AnsibleRole)


def job_type(item):
    return isinstance(item, ZuulJob)


def block_type(item):
    if role_type(item):
        return "role"
    elif job_type(item):
        return "job"
    raise ValueError("Unsupported type: {}".format(type(item)))


def class_from_block_type(block_type):
    if block_type == "role":
        return AnsibleRole
    elif block_type == "job":
        return ZuulJob
    raise ValueError("No class for block type: {}".format(block_type))


def init_elasticsearch(app):
    init_elasticsearch_con(
        app.config["ES_HOST"],
        app.config.get("ES_USER"),
        app.config.get("ES_PASSWORD"),
        app.config.get("ES_PORT"),
        app.config.get("ES_INDEX_PREFIX"),
    )

    app.add_template_test(role_type)
    app.add_template_test(job_type)
    app.add_template_filter(block_type)


def init_elasticsearch_con(
    host, user=None, password=None, port=None, es_index_prefix=None
):
    http_auth = None
    # Set authentication parameters if available
    if user and password:
        http_auth = (user, password)
    if port is None:
        port = DEFAULT_ES_PORT
    connections.create_connection(host=host, http_auth=http_auth, port=port)

    # NOTE (felix): Hack to override the index names with prefix from config
    # TODO (felix): Remove this once https://github.com/elastic/elasticsearch-dsl-py/pull/1099
    # is merged and use the pattern described in the elasticsearch-dsl documentation
    # https://elasticsearch-dsl.readthedocs.io/en/latest/persistence.html#index
    #
    # Unfortunately, this pattern is currently only working for document.init(),
    # while the search() and save() methods will still use the original index name
    # set in the index-meta class.
    # This unexpected behaviour is also described in
    # https://github.com/elastic/elasticsearch-dsl-py/issues/1121 and
    # https://github.com/elastic/elasticsearch-dsl-py/issues/1091.
    if es_index_prefix is not None:
        # If the user set a '-' at the end of the prefix, we don't want to end
        # up in messy index names
        es_index_prefix = es_index_prefix.rstrip("-")
        for idx_cls in [ZuulJob, AnsibleRole, ZuulTenant, GitRepo]:
            # NOTE (felix): Index.name seems to hold the constant value that we defined
            # in our index-meta class for the document. _index._name on the other hand
            # holds the active value. Thus, we can use this to ensure that the prefix
            # is only prepended once, even if we call this method multiple times.
            idx_cls._index._name = "{}-{}".format(es_index_prefix, idx_cls.Index.name)

    ZuulJob.init()
    AnsibleRole.init()
    ZuulTenant.init()
    GitRepo.init()
