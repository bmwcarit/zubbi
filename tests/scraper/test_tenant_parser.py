# Copyright 2024 BMW Car IT GmbH
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

from zubbi.scraper.tenant_parser import TenantParser


def test_parse():
    expected_repo_map = {
        "orga1/repo1": {
            "tenants": {
                "jobs": ["bar"],
                "roles": ["foo", "bar"],
                "extra_config_paths": {"zuul-extra.d": ["foo"]},
            },
            "connection_name": "github",
        },
        "orga1/repo2": {
            "tenants": {"jobs": ["foo"], "roles": ["foo"]},
            "connection_name": "github",
        },
        "orga1/repo3": {
            "tenants": {"jobs": ["foo"], "roles": ["foo"]},
            "connection_name": "github",
        },
        "orga1/repo4": {
            "tenants": {"jobs": ["foo"], "roles": ["foo"]},
            "connection_name": "github",
        },
        "orga2/repo1": {
            "tenants": {"jobs": ["foo", "bar"], "roles": ["foo", "bar"]},
            "connection_name": "github",
        },
        "orga2/repo2": {
            "tenants": {"jobs": ["foo"], "roles": ["foo", "bar"]},
            "connection_name": "github",
        },
        "orga2/repo3": {
            "tenants": {"jobs": ["foo"], "roles": ["foo"]},
            "connection_name": "github",
        },
    }

    tenant_parser = TenantParser(
        sources_file="tests/testdata/tenant_configs/tenant-config.yaml"
    )
    tenant_parser.parse()

    assert tenant_parser.repo_map == expected_repo_map
