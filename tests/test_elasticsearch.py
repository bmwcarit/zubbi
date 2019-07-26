import ssl
from unittest import mock

import elasticsearch_dsl
import pytest
from elasticsearch_dsl.serializer import serializer

from zubbi.models import (
    AnsibleRole,
    GitRepo,
    init_elasticsearch_con,
    ZuulJob,
    ZuulTenant,
)


@pytest.fixture(scope="function")
def elmock():
    with mock.patch.object(elasticsearch_dsl.connections, "Elasticsearch") as _elmock:
        yield _elmock

    # Reset the name of each index to its original value as it might have changed
    # during the tests. Btw, this clearly shows that this is a hack ;-)
    for idx_cls in [ZuulJob, AnsibleRole, ZuulTenant, GitRepo]:
        # As the Index.name attribute holds the constant value from the original
        # definition, we can use it to reset the active value which might have
        # changed due to the index_prefix hack.
        idx_cls._index._name = idx_cls.Index.name


def test_elasticsearch_init_ssl_defaults(elmock):
    tls_config = {"enabled": True}
    init_elasticsearch_con("127.0.0.1", "user", "password", 443, tls=tls_config)

    # Use single assertion for each argument as we can't compare the ssl_context so easily
    kwargs = elmock.call_args[1]
    assert kwargs["port"] == 443
    assert kwargs["use_ssl"] is True
    assert kwargs["ssl_context"].check_hostname is True
    assert kwargs["ssl_context"].verify_mode == ssl.CERT_REQUIRED


def test_elasticsearch_init_ssl(elmock):
    tls_config = {"enabled": True, "check_hostname": False, "verify_mode": "CERT_NONE"}
    init_elasticsearch_con("127.0.0.1", "user", "password", 443, tls=tls_config)

    kwargs = elmock.call_args[1]
    assert kwargs["port"] == 443
    assert kwargs["use_ssl"] is True
    assert kwargs["ssl_context"].check_hostname is False
    assert kwargs["ssl_context"].verify_mode == ssl.CERT_NONE


def test_elasticsearch_init(elmock):

    # Define the existing indices for the mock
    existing_indices = {"zuul-jobs", "ansible-roles", "unknown-index"}
    elmock.return_value.indices.exists.side_effect = (
        lambda index: index in existing_indices
    )

    init_elasticsearch_con("127.0.0.1", "user", "password")

    # Validate that the Elasticsearch() (which is called by elasticsearch-dsl in the end)
    # was called with the correct arguments.
    assert elmock.call_args == mock.call(
        host="127.0.0.1",
        port=9200,
        http_auth=("user", "password"),
        use_ssl=False,
        ssl_context=None,
        serializer=serializer,
    )

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


def test_elasticsearch_init_with_prefix(elmock):

    # Define the existing indices for the mock
    existing_indices = {"zubbi-zuul-jobs", "zubbi-ansible-roles", "unknown-index"}
    elmock.return_value.indices.exists.side_effect = (
        lambda index: index in existing_indices
    )

    init_elasticsearch_con("127.0.0.1", "user", "password", index_prefix="zubbi")

    # Validate that the Elasticsearch() (which is called by elasticsearch-dsl in the end)
    # was called with the correct arguments.
    assert elmock.call_args == mock.call(
        host="127.0.0.1",
        port=9200,
        http_auth=("user", "password"),
        use_ssl=False,
        ssl_context=None,
        serializer=serializer,
    )

    # Validate that all necessary indices were checked for existence
    checked_indices = {
        call[1]["index"] for call in elmock.return_value.indices.exists.call_args_list
    }
    assert {
        "zubbi-zuul-jobs",
        "zubbi-ansible-roles",
        "zubbi-zuul-tenants",
        "zubbi-git-repos",
    } == checked_indices

    # Validate that only the missing indices were created
    created_indices = {
        call[1]["index"] for call in elmock.return_value.indices.create.call_args_list
    }
    assert {"zubbi-zuul-tenants", "zubbi-git-repos"} == created_indices


def test_elasticsearch_init_with_empty_prefix(elmock):

    # Define the existing indices for the mock
    existing_indices = {"zuul-jobs", "ansible-roles", "unknown-index"}
    elmock.return_value.indices.exists.side_effect = (
        lambda index: index in existing_indices
    )

    init_elasticsearch_con("127.0.0.1", "user", "password", index_prefix="")

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


def test_elasticsearch_init_with_prefix_multi(elmock):

    # Define the existing indices for the mock
    existing_indices = {"zubbi-zuul-jobs", "zubbi-ansible-roles", "unknown-index"}
    elmock.return_value.indices.exists.side_effect = (
        lambda index: index in existing_indices
    )

    init_elasticsearch_con("127.0.0.1", "user", "password", index_prefix="zubbi")
    init_elasticsearch_con("127.0.0.1", "user", "password", index_prefix="zubbi")

    # Evenv if we called the init() method multiple times, the index should only be
    # prepended once.
    checked_indices = {
        call[1]["index"] for call in elmock.return_value.indices.exists.call_args_list
    }
    assert {
        "zubbi-zuul-jobs",
        "zubbi-ansible-roles",
        "zubbi-zuul-tenants",
        "zubbi-git-repos",
    } == checked_indices


def test_elasticsearch_write(elmock):
    init_elasticsearch_con("127.0.0.1", "user", "password")

    zt = ZuulTenant(name="foo")
    zt.save()

    assert elmock.return_value.index.call_args == mock.call(
        index="zuul-tenants", body=zt.to_dict()
    )


def test_elasticsearch_write_with_prefix(elmock):
    init_elasticsearch_con("127.0.0.1", "user", "password", index_prefix="zubbi")

    zt = ZuulTenant(name="foo")
    zt.save()

    assert elmock.return_value.index.call_args == mock.call(
        index="zubbi-zuul-tenants", body=zt.to_dict()
    )
