import contextlib
import importlib
import os
import ssl
from unittest import mock

import elasticsearch
import pytest

import zubbi.models
from zubbi.models import (
    ZUBBI_INDEX_PREFIX_ENV,
    init_elasticsearch_con,
    init_elasticsearch_documents,
)

ES_HOST = "http://127.0.0.1:9200"
ES_HOST_SSL = "https://127.0.0.1:443"


@pytest.fixture()
def mock_index_prefix():
    # Using a ctx manager allows us to pass different prefix values in each
    # test case.
    @contextlib.contextmanager
    def _index_prefix(prefix):
        # Keep the original prefix, so we can restore it later on
        original_prefix = os.environ.get(ZUBBI_INDEX_PREFIX_ENV)
        os.environ[ZUBBI_INDEX_PREFIX_ENV] = prefix
        # As the index prefix envvar is used in the class definition of our
        # module classes, we have to reload the imports after the envvar is
        # set. Otherwise, setting the envvar has no effect as the classes
        # were already created without index prefix.
        # NOTE (felix): This won't have any effect on objects imported via
        # from ... import ... statements as the object definition will not
        # be redefined if it's already imported. If a specific object is
        # required, either use the full-qualified object name or import
        # the object within the context manager.
        importlib.reload(zubbi.models)

        yield

        # Cleanup: Delete the envvar (or restore the original value) and
        # reload the import, so that subsequent tests can work without
        # the index prefix.
        if original_prefix is not None:
            os.environ[ZUBBI_INDEX_PREFIX_ENV] = original_prefix
        else:
            del os.environ[ZUBBI_INDEX_PREFIX_ENV]
        importlib.reload(zubbi.models)

    return _index_prefix


class DummyElasticsearch(elasticsearch.Elasticsearch):
    # We use this dummy ES client to evaluate that the connection
    # parameters (args, kwargs) are passed correctly to the underlying ES
    # connection.
    def __init__(self, *args, hosts, **kwargs):
        self.hosts = hosts
        self.args = args
        self.kwargs = kwargs


@pytest.fixture()
def dummy_es_con():
    dummy_es = elasticsearch.dsl.connections.Connections[DummyElasticsearch](
        elasticsearch_class=DummyElasticsearch
    )

    with mock.patch("zubbi.models.connections", dummy_es) as _elmock:
        yield _elmock


def test_elasticsearch_init_ssl_defaults(dummy_es_con):
    tls_config = {"enabled": True}
    init_elasticsearch_con(ES_HOST_SSL, "user", "password", tls=tls_config)

    default = dummy_es_con.get_connection()
    # Use single assertion for each argument as we can't compare the ssl_context so easily
    assert default.hosts == ES_HOST_SSL
    assert default.kwargs["basic_auth"] == ("user", "password")
    assert default.kwargs["ssl_context"].check_hostname is True
    assert default.kwargs["ssl_context"].verify_mode == ssl.CERT_REQUIRED


def test_elasticsearch_init_ssl(dummy_es_con):
    tls_config = {"enabled": True, "check_hostname": False, "verify_mode": "CERT_NONE"}
    init_elasticsearch_con(ES_HOST_SSL, "user", "password", tls=tls_config)

    default = dummy_es_con.get_connection()
    assert default.hosts == ES_HOST_SSL
    assert default.kwargs["basic_auth"] == ("user", "password")
    assert default.kwargs["ssl_context"].check_hostname is False
    assert default.kwargs["ssl_context"].verify_mode == ssl.CERT_NONE


@mock.patch("elasticsearch.Elasticsearch")
def test_elasticsearch_init(elmock):
    existing_indices = {"zuul-jobs", "ansible-roles", "unknown-index"}
    elmock.return_value.indices.exists.side_effect = (
        lambda index: index in existing_indices
    )

    init_elasticsearch_documents(using=elmock())

    # Validate that all necessary indices were checked for existence
    checked_indices = {
        call[1]["index"] for call in elmock.return_value.indices.exists.call_args_list
    }
    assert {
        "zuul-jobs",
        "ansible-roles",
        "zuul-tenants",
        "git-repos",
    } == checked_indices

    # Validate that only the missing indices were created
    created_indices = {
        call[1]["index"] for call in elmock.return_value.indices.create.call_args_list
    }
    assert {"zuul-tenants", "git-repos"} == created_indices


@mock.patch("elasticsearch.Elasticsearch")
def test_elasticsearch_init_with_prefix(elmock, mock_index_prefix):
    index_prefix = "zubbi"
    with mock_index_prefix(index_prefix):
        existing_indices = {
            f"{index_prefix}-zuul-jobs",
            f"{index_prefix}-ansible-roles",
            "unknown-index",
        }
        elmock.return_value.indices.exists.side_effect = (
            lambda index: index in existing_indices
        )

        init_elasticsearch_documents(using=elmock())

        # Validate that all necessary indices were checked for existence
        checked_indices = {
            call[1]["index"]
            for call in elmock.return_value.indices.exists.call_args_list
        }
        assert {
            f"{index_prefix}-zuul-jobs",
            f"{index_prefix}-ansible-roles",
            f"{index_prefix}-zuul-tenants",
            f"{index_prefix}-git-repos",
        } == checked_indices

        # Validate that only the missing indices were created
        created_indices = {
            call[1]["index"]
            for call in elmock.return_value.indices.create.call_args_list
        }
        assert {
            f"{index_prefix}-zuul-tenants",
            f"{index_prefix}-git-repos",
        } == created_indices


@mock.patch("elasticsearch.Elasticsearch")
def test_elasticsearch_init_with_empty_prefix(elmock, mock_index_prefix):
    with mock_index_prefix(""):
        # Define the existing indices for the mock
        existing_indices = {"zuul-jobs", "ansible-roles", "unknown-index"}
        elmock.return_value.indices.exists.side_effect = (
            lambda index: index in existing_indices
        )

        init_elasticsearch_documents(using=elmock())

        # Validate that all necessary indices were checked for existence
        checked_indices = {
            call[1]["index"]
            for call in elmock.return_value.indices.exists.call_args_list
        }
        assert {
            "zuul-jobs",
            "ansible-roles",
            "zuul-tenants",
            "git-repos",
        } == checked_indices

        # Validate that only the missing indices were created
        created_indices = {
            call[1]["index"]
            for call in elmock.return_value.indices.create.call_args_list
        }
        assert {"zuul-tenants", "git-repos"} == created_indices


@mock.patch("elasticsearch.Elasticsearch")
def test_elasticsearch_init_with_prefix_multi(elmock, mock_index_prefix):
    with mock_index_prefix("zubbi"):
        # Define the existing indices for the mock
        existing_indices = {"zubbi-zuul-jobs", "zubbi-ansible-roles", "unknown-index"}
        elmock.return_value.indices.exists.side_effect = (
            lambda index: index in existing_indices
        )

        init_elasticsearch_documents(using=elmock())
        init_elasticsearch_documents(using=elmock())

        # Evenv if we called the init() method multiple times, the index should only be
        # prepended once.
        checked_indices = {
            call[1]["index"]
            for call in elmock.return_value.indices.exists.call_args_list
        }
        assert {
            "zubbi-zuul-jobs",
            "zubbi-ansible-roles",
            "zubbi-zuul-tenants",
            "zubbi-git-repos",
        } == checked_indices


@mock.patch("elasticsearch.Elasticsearch")
def test_elasticsearch_write(elmock):
    # See comment in test_elasticsearch_write_with_prefix test function.
    from zubbi.models import ZuulTenant

    ZuulTenant.init(using=elmock())
    zt = ZuulTenant(name="foo")
    zt.save(using=elmock())

    assert elmock.return_value.index.call_args == mock.call(
        index="zuul-tenants", body=zt.to_dict()
    )


@mock.patch("elasticsearch.Elasticsearch")
def test_elasticsearch_write_with_prefix(elmock, mock_index_prefix):
    with mock_index_prefix("zubbi"):
        # Keep the import within the mock_index_prefix fixture or use
        # the full-qualified module name. If the ZuulTenant is already
        # imported outside of the fixture, the importlib.reload() call
        # within the fixture won't have any effect as the ZuulTenant
        # object is already defined.
        from zubbi.models import ZuulTenant

        ZuulTenant.init(using=elmock())
        zt = ZuulTenant(name="foo")
        zt.save(using=elmock())

        assert elmock.return_value.index.call_args == mock.call(
            index="zubbi-zuul-tenants", body=zt.to_dict()
        )
