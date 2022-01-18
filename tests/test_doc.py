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

import pytest

from zubbi.doc import render_markdown, render_sphinx


@pytest.mark.parametrize(
    "readme, expected",
    [
        ("Hello World!", "<p>Hello World!</p>\n"),
        ("**Hello World!**", "<p><strong>Hello World!</strong></p>\n"),
        ("# Hello World!", "<h1>Hello World!</h1>\n"),
    ],
)
def test_render_markdown_simple(readme, expected):
    result = render_markdown(readme)
    assert expected == result["html"]


@pytest.mark.parametrize(
    "readme, expected",
    [
        ("Hello World!", "<p>Hello World!</p>\n"),
        ("**Hello World!**", "<p><strong>Hello World!</strong></p>\n"),
    ],
)
def test_render_sphinx_simple(readme, expected):
    result = render_sphinx(readme)
    assert expected == result["html"]


def test_render_sphinx_python_code(readme_python_code):
    expected_code = (
        '<div class="highlight-python notranslate">'
        '<div class="highlight"><pre><span></span>'
        '<span class="kn">import</span> <span class="nn">'
        "this</span>\n</pre></div>\n</div>\n"
    )

    result = render_sphinx(readme_python_code)
    assert expected_code == result["html"]


def test_render_sphinx_yaml_code(readme_yaml_code):
    expected_code = (
        '<div class="highlight-yaml notranslate"><div class="highlight">'
        '<pre><span></span><span class="p p-Indicator">-</span>'
        '<span class="w"> </span><span class="nt">job</span>'
        '<span class="p">:</span><span class="w"></span>\n'
        '<span class="w">    </span><span class="nt">name</span>'
        '<span class="p">:</span><span class="w"> </span>'
        '<span class="l l-Scalar l-Scalar-Plain">foo</span><span class="w"></span>\n'
        '<span class="w">    </span><span class="nt">parent</span>'
        '<span class="p">:</span><span class="w"> </span>'
        '<span class="l l-Scalar l-Scalar-Plain">bar</span><span class="w"></span>\n'
        '<span class="w">    </span><span class="nt">playbook</span>'
        '<span class="p">:</span><span class="w"> </span>'
        '<span class="l l-Scalar l-Scalar-Plain">foo-bar.yaml</span><span class="w"></span>\n'
        "</pre></div>\n"
        "</div>\n"
    )

    result = render_sphinx(readme_yaml_code)
    assert expected_code == result["html"]


def test_render_sphinx_supported_os(readme_supported_os):
    expected_platforms = ["linux", "windows"]
    expected_html = "<p>This works on Linux and Windows!</p>\n"

    result = render_sphinx(readme_supported_os)

    assert expected_platforms == result["platforms"]
    assert expected_html == result["html"]


def test_render_sphinx_reusable(readme_reusable):
    expected_reusable = True
    expected_html = "<p>This is a reusable role!</p>\n"

    result = render_sphinx(readme_reusable)

    assert expected_reusable == result["reusable"]
    assert expected_html == result["html"]
