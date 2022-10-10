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

from setuptools import find_packages, setup


description = "Index for finding jobs & roles used in a Zuul based CI system"


with open("README.md") as readme:
    long_description = readme.read()


requires = [
    "arrow",
    "click",
    "elasticsearch-dsl>=7.0.0",
    "pyyaml",
    "pyjwt",
    "pyzmq",
    "cachelib",
    "cryptography",
    "requests",
    "flask",
    "github3.py",
    "zuul-sphinx",
    "sphinx",
    "jinja2",
    "readme_renderer[md]",
    "tabulate",
    "gitpython",
    "markupsafe",
]

setup(
    name="zubbi",
    description=description,
    author="Benedikt Loeffler, Felix Edel, Simon Westphahl",
    author_email="benedikt.loeffler@bmw.de, felix.edel@bmw.de, "
    "simon.westphahl@bmw.de",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    install_requires=requires,
    url="https://github.com/bmwcarit/zubbi",
    license="Apache License 2.0",
    use_scm_version={"version_scheme": "post-release"},
    setup_requires=["setuptools_scm"],
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    entry_points={
        "console_scripts": ["zubbi-scraper = zubbi.scraper.main:main"],
        "flask.commands": ["collectstatic=zubbi.cli:collectstatic"],
    },
    classifiers={
        "Development Status :: 5 - Production/Stable",
        "Framework :: Flask",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3 :: Only",
    },
)
