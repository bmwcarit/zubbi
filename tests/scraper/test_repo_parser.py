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

from datetime import datetime, timezone

from zubbi.scraper.repo_parser import RepoParser


JOB_1_SHA = "83bf1474a8a84cc1dddc8da435e2e4d9f4bbdeb1"
JOB_2_SHA = "1e4008e1c0f4511579e49854c34905b419441331"
JOB_3_SHA = "728e71a5ab9d095d7b983aee6db6ea4656072658"
ROLE_1_SHA = "a336b3fdba7cd8ad535350fd7d249b7285670dfd"
ROLE_2_SHA = "f39ee170837cb6a91cbb3d7f9def7584a3a27919"


def test_parse(repo_data):
    scrape_time = datetime.now(timezone.utc)
    # Extract test data from fixture function result
    repo, tenants, job_files, role_files = repo_data

    jobs, roles = RepoParser(
        repo, tenants, job_files, role_files, scrape_time, is_reusable_repo=False
    ).parse()

    # We assume that we can access the resulting jobs and roles dictionary
    # with the given SHA values. Otherwise, we will get a KeyError.
    job_1 = jobs[0]
    job_2 = jobs[1]
    job_3 = jobs[2]
    job_4 = jobs[3]
    role_1 = [r for r in roles if r["role_name"] == "foo"][0]
    role_2 = [r for r in roles if r["role_name"] == "bar"][0]

    expected_job_1 = {
        "job_name": "my-cool-new-job",
        "repo": "my/project",
        "tenants": ["foo"],
        "description": "This is just a job for testing purposes.\n\n"
        ".. supported_os:: Linux\n\n"
        ".. reusable:: True\n",
        "description_html": "<p>This is just a job for testing purposes.</p>\n",
        "parent": "cool-base-job",
        "url": "https://github/zuul.d/jobs.yaml",
        "private": False,
        "platforms": ["linux"],
        "reusable": True,
        "scrape_time": scrape_time,
        "line_start": 1,
        "line_end": 11,
        "last_updated": None,
    }

    expected_job_2 = {
        "job_name": "another-job",
        "repo": "my/project",
        "tenants": ["foo"],
        "description": "This time without a playbook and a parent.\n",
        "description_html": "<p>This time without a playbook and a parent.</p>\n",
        "parent": "base",
        "url": "https://github/zuul.d/jobs.yaml",
        "private": False,
        "platforms": [],
        "reusable": False,
        "scrape_time": scrape_time,
        "line_start": 12,
        "line_end": 16,
        "last_updated": None,
    }

    expected_job_3 = {
        "job_name": "cool-base-job",
        "repo": "my/project",
        "tenants": ["foo"],
        "description": "This is a base job with explicitly no parent.\n",
        "description_html": "<p>This is a base job with explicitly no parent.</p>\n",
        "parent": None,
        "url": "https://github/zuul.d/jobs.yaml",
        "private": False,
        "platforms": [],
        "reusable": False,
        "line_start": 17,
        "line_end": 22,
        "scrape_time": scrape_time,
        "last_updated": None,
    }

    expected_job_4 = {
        "job_name": "no-description-job",
        "repo": "my/project",
        "tenants": ["foo"],
        "parent": None,
        "url": "https://github/zuul.d/jobs.yaml",
        "private": False,
        "reusable": False,
        "line_start": 23,
        "line_end": 25,
        "scrape_time": scrape_time,
        "last_updated": None,
    }

    expected_role_1 = {
        "role_name": "foo",
        "repo": "my/project",
        "tenants": ["foo", "bar"],
        "description": "Just some simple description\n\n"
        ".. supported_os:: Linux, Windows\n\n"
        ".. reusable:: True\n",
        "description_html": "<p>Just some simple description</p>\n",
        "url": "https://github/my/project/tree/master/roles/foo",
        "private": False,
        "platforms": ["linux", "windows"],
        "reusable": True,
        "scrape_time": scrape_time,
        "last_updated": "2018-09-17 15:15:15",
    }

    expected_role_2 = {
        "role_name": "bar",
        "repo": "my/project",
        "tenants": ["foo", "bar"],
        "description": (
            "Role description containing some reStructuredText expressions.\n\n"
            "**Role variables**\n\n"
            ".. zuul:rolevar:: mandatory_variable\n\n"
            "   This variable is mandatory.\n\n\n"
            ".. zuul:rolevar:: optional_variable\n"
            "   :default: some_value\n\n"
            "   This one is not.\n\n\n"
            ".. zuul:rolevar:: list_variable\n"
            "   :default: []\n"
            "   :type: list\n\n"
            "   This one must be a list.\n"
        ),
        "description_html": (
            "<p>Role description containing some reStructuredText expressions.</p>\n"
            "<p><strong>Role variables</strong></p>\n"
            '<dl class="zuul rolevar">\n'
            '<dt class="sig sig-object zuul" id="rolevar-mandatory_variable">\n'
            '<span class="sig-name descname">'
            '<span class="pre">mandatory_variable</span>'
            "</span>"
            '<a class="headerlink" href="#rolevar-mandatory_variable" '
            'title="Permalink to this definition">'
            "¶</a><br /></dt>\n"
            "<dd><p>This variable is mandatory.</p>\n"
            "</dd></dl>\n"
            "\n"
            '<dl class="zuul rolevar">\n'
            '<dt class="sig sig-object zuul" id="rolevar-optional_variable">\n'
            '<span class="sig-name descname">'
            '<span class="pre">optional_variable</span>'
            "</span>"
            '<a class="headerlink" href="#rolevar-optional_variable" '
            'title="Permalink to this definition">'
            '¶</a><br /><span class="pre">Default:</span> '
            '<code class="docutils literal notranslate"><span class="pre">'
            "some_value</span></code><br /></dt>\n"
            "<dd><p>This one is not.</p>\n"
            "</dd></dl>\n"
            "\n"
            '<dl class="zuul rolevar">\n'
            '<dt class="sig sig-object zuul" id="rolevar-list_variable">\n'
            '<span class="sig-name descname">'
            '<span class="pre">list_variable</span>'
            "</span>"
            '<a class="headerlink" href="#rolevar-list_variable" '
            'title="Permalink to this definition">¶</a><br />'
            '<span class="pre">Default:</span> '
            '<code class="docutils literal notranslate"><span class="pre">[]</span>'
            '</code><br /><span class="pre">Type:</span> <em><span class="pre">'
            "list</span></em><br /></dt>\n"
            "<dd><p>This one must be a list.</p>\n"
            "</dd></dl>\n"
            "\n"
        ),
        "url": "https://github/my/project/tree/master/roles/bar",
        "private": False,
        "platforms": [],
        "reusable": False,
        "scrape_time": scrape_time,
        "last_updated": "2018-09-17 15:15:15",
    }

    # NOTE (fschmidt): Without the skip_empty flag, empty (= None) keys will
    # be stripped from the resulting dict.
    assert job_1.to_dict(skip_empty=False) == expected_job_1
    assert job_2.to_dict(skip_empty=False) == expected_job_2
    assert job_3.to_dict(skip_empty=False) == expected_job_3
    assert job_4.to_dict(skip_empty=False) == expected_job_4
    assert role_1.to_dict(skip_empty=False) == expected_role_1
    assert role_2.to_dict(skip_empty=False) == expected_role_2


def test_parse_reusable_repo(repo_data):
    scrape_time = datetime.now(timezone.utc)
    # Extract test data from fixture function result
    repo, tenants, job_files, role_files = repo_data

    jobs, roles = RepoParser(
        repo, tenants, job_files, role_files, scrape_time, is_reusable_repo=True
    ).parse()

    # We assume that we can access the resulting jobs and roles dictionary
    # with the given SHA values. Otherwise, we will get a KeyError.
    job_1 = jobs[0]
    job_2 = jobs[1]
    job_3 = jobs[2]
    job_4 = jobs[3]
    role_1 = [r for r in roles if r["role_name"] == "foo"][0]
    role_2 = [r for r in roles if r["role_name"] == "bar"][0]

    # Repo parsed as reusable = True, all jobs and roles should have reusable==True
    assert job_1.to_dict(skip_empty=False)["reusable"]
    assert job_2.to_dict(skip_empty=False)["reusable"]
    assert job_3.to_dict(skip_empty=False)["reusable"]
    assert job_4.to_dict(skip_empty=False)["reusable"]
    assert role_1.to_dict(skip_empty=False)["reusable"]
    assert role_2.to_dict(skip_empty=False)["reusable"]
